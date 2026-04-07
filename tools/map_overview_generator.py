"""Generate a high-resolution world map overview image.

Each biome is rendered as a separate 1024×768 cartographic panel with
a representative symbol (boss, landmark, or key NPC), then all panels
are stitched into a single large image.

For shattered_realms (3×3 biome grid), the final image is 3072×2304.

Usage:
    python tools/map_overview_generator.py

Requires ComfyUI running on the configured API endpoint.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from tools.comfyui_batch_generator import (
        GenerationTask, submit_prompt, wait_for_completion,
        get_output_images, copy_output_to_project, _name_to_seed,
        _build_txt2img_workflow,
    )
    from tools.model_profile import get_active_profile
except ImportError:
    from comfyui_batch_generator import (  # type: ignore
        GenerationTask, submit_prompt, wait_for_completion,
        get_output_images, copy_output_to_project, _name_to_seed,
        _build_txt2img_workflow,
    )
    from model_profile import get_active_profile  # type: ignore


# ── Configuration ──────────────────────────────────────────────────────

def _cell_size() -> tuple[int, int]:
    return get_active_profile().map_panel_resolution

_MAP_STYLE = (
    "hand-drawn fantasy world map, cartographic ink illustration on aged "
    "parchment, top-down bird's eye view, vintage atlas style, "
    "detailed pen and ink with watercolor wash, ornamental border, "
    "D&D campaign map, masterpiece, best quality"
)

_MAP_NEGATIVE = (
    "photorealistic, 3d render, modern, photograph, person close-up, "
    "portrait, text, watermark, blurry, low quality, anime, cartoon"
)

# Map from entity types to cartographic icon descriptions
_ENTITY_ICON_STYLE = {
    "enemy": "menacing creature icon drawn in dark ink",
    "npc": "figure icon drawn in warm sepia ink",
    "object": "artifact symbol drawn in detailed ink",
    "player": "heroic figure icon in golden ink",
}


# ── Biome representative selection ─────────────────────────────────────


@dataclass
class BiomeRepresentative:
    """The most notable feature of a biome for map iconography."""
    biome_id: str
    name: str
    description: str
    icon_type: str  # "creature", "landmark", "figure", "artifact"


# Priority: boss enemies > named NPCs > quest objects > lexicon landmarks
def _select_representative(
    biome_id: str,
    tiles: list[dict],
    lexicon: dict,
) -> BiomeRepresentative:
    """Pick the single most iconic element from a biome's tiles."""
    bosses = []
    npcs = []
    objects = []

    for tile in tiles:
        for e in tile.get("entities", []):
            name = e.get("name", "")
            etype = (e.get("entity_type") or "").lower()
            if not name:
                continue
            # Skip generic creatures
            if name.lower() in (
                "goblin", "wolf", "bat", "spider", "skeleton", "zombie",
                "rat", "bandit", "guard", "thug",
            ):
                continue
            if etype in ("enemy", "monster", "hostile"):
                bosses.append(name)
            elif etype == "npc":
                npcs.append(name)
            elif etype == "object":
                objects.append(name)

    # Pick the best representative
    if bosses:
        name = bosses[0]
        return BiomeRepresentative(
            biome_id, name,
            f"{name}, {_ENTITY_ICON_STYLE['enemy']}",
            "creature",
        )
    if npcs:
        name = npcs[0]
        return BiomeRepresentative(
            biome_id, name,
            f"{name}, {_ENTITY_ICON_STYLE['npc']}",
            "figure",
        )
    if objects:
        name = objects[0]
        return BiomeRepresentative(
            biome_id, name,
            f"{name}, {_ENTITY_ICON_STYLE['object']}",
            "artifact",
        )

    # Fallback: lexicon landmark
    biome_lex = lexicon.get(biome_id, {})
    landmarks = biome_lex.get("landmarks", [])
    if landmarks:
        return BiomeRepresentative(
            biome_id, landmarks[0],
            f"{landmarks[0]}, drawn as a map symbol in ink",
            "landmark",
        )

    return BiomeRepresentative(
        biome_id, biome_id.replace("_", " ").title(),
        f"symbolic terrain icon for {biome_id.replace('_', ' ')}",
        "landmark",
    )


# ── Per-biome prompt builder ──────────────────────────────────────────


def _build_biome_map_prompt(
    biome_id: str,
    rep: BiomeRepresentative,
    lexicon: dict,
) -> str:
    """Build a cartographic prompt for one biome cell."""
    biome_lex = lexicon.get(biome_id, {})
    palette = biome_lex.get("palette", "")
    mood = biome_lex.get("mood", "")
    biome_name = biome_id.replace("_", " ")

    parts = [
        _MAP_STYLE,
        f"region labeled {biome_name}",
        f"central icon: {rep.description}",
    ]

    # Add one landmark as terrain flavor
    landmarks = biome_lex.get("landmarks", [])
    if landmarks:
        parts.append(f"small terrain detail: {landmarks[0]}")

    if palette:
        parts.append(f"color palette: {palette}")
    if mood:
        parts.append(f"atmosphere: {mood}")

    return ", ".join(parts)


# ── Generation ────────────────────────────────────────────────────────


def generate_biome_panel(
    biome_id: str,
    prompt: str,
    output_path: Path,
    seed_offset: int = 0,
) -> bool:
    """Generate a single biome map panel via ComfyUI."""
    profile = get_active_profile()
    cell_w, cell_h = _cell_size()
    task = GenerationTask(
        task_type="background",
        entity_name=f"map_{biome_id}",
        prompt=prompt,
        negative=profile.negative_map if profile.supports_negative else "",
        output_path=str(output_path),
        seed=_name_to_seed(f"map_overview_{biome_id}", offset=8000 + seed_offset),
        steps=profile.steps_people,
        cfg=profile.cfg_map,
        width=cell_w,
        height=cell_h,
        checkpoint=profile.checkpoint,
        vae=profile.vae or profile.checkpoint,
    )

    workflow = _build_txt2img_workflow(task)
    prompt_id = submit_prompt(workflow)
    if not prompt_id:
        return False

    history = wait_for_completion(prompt_id, timeout=180)
    if not history:
        return False

    images = get_output_images(history)
    if not images:
        return False

    return copy_output_to_project(images[0]["filename"], str(output_path))


def stitch_panels(
    panels: dict[str, Path],
    grid_layout: list[list[str]],
    output_path: Path,
) -> bool:
    """Stitch individual biome panels into a single large map image.

    Uses pure Python PNG reading via Qt (already available) or falls
    back to a simple raw copy if PIL is not installed.
    """
    try:
        from PyQt5.QtGui import QImage, QPainter
        from PyQt5.QtCore import QRect
    except ImportError:
        print("[ERROR] PyQt5 required for image stitching")
        return False

    rows = len(grid_layout)
    cols = len(grid_layout[0]) if grid_layout else 0
    cell_w, cell_h = _cell_size()
    total_w = cols * cell_w
    total_h = rows * cell_h

    canvas = QImage(total_w, total_h, QImage.Format_RGB32)
    canvas.fill(0xFF1a1510)  # dark parchment fallback

    painter = QPainter(canvas)
    for row_idx, row in enumerate(grid_layout):
        for col_idx, biome_id in enumerate(row):
            panel_path = panels.get(biome_id)
            if not panel_path or not panel_path.exists():
                print(f"  [WARN] Missing panel for {biome_id}")
                continue
            cell_img = QImage(str(panel_path))
            if cell_img.isNull():
                print(f"  [WARN] Failed to load {panel_path}")
                continue
            x = col_idx * cell_w
            y = row_idx * cell_h
            painter.drawImage(
                QRect(x, y, cell_w, cell_h),
                cell_img,
            )
    painter.end()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(str(output_path), "PNG")
    print(f"[INFO] Stitched map saved to {output_path} ({total_w}x{total_h})")
    return True


def generate_coordinate_mapping(
    grid_layout: list[list[str]],
    biome_layout: dict,
    output_path: Path,
) -> None:
    """Write a JSON file mapping pixel regions to biome/tile coordinates."""
    cell_w, cell_h = _cell_size()
    mapping = {
        "image_width": len(grid_layout[0]) * cell_w,
        "image_height": len(grid_layout) * cell_h,
        "cell_width": cell_w,
        "cell_height": cell_h,
        "grid": [],
    }

    blocks = biome_layout.get("blocks", [])
    block_map = {b["biome"]: b for b in blocks}

    for row_idx, row in enumerate(grid_layout):
        for col_idx, biome_id in enumerate(row):
            block = block_map.get(biome_id, {})
            tile_rows = block.get("rows", [0, 0])
            tile_cols = block.get("cols", [0, 0])
            mapping["grid"].append({
                "biome": biome_id,
                "pixel_x": col_idx * cell_w,
                "pixel_y": row_idx * cell_h,
                "pixel_w": cell_w,
                "pixel_h": cell_h,
                "tile_row_range": tile_rows,
                "tile_col_range": tile_cols,
            })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    print(f"[INFO] Coordinate mapping saved to {output_path}")


# ── Main ──────────────────────────────────────────────────────────────


def main() -> int:
    map_path = _PROJECT_ROOT / "workspace" / "shattered_realms" / "map.json"
    lexicon_path = _PROJECT_ROOT / "workspace" / "shattered_realms" / "biome_lexicon.json"

    if not map_path.exists():
        print(f"[ERROR] {map_path} not found")
        return 1

    raw = json.loads(map_path.read_text(encoding="utf-8"))
    lexicon = json.loads(lexicon_path.read_text(encoding="utf-8")) if lexicon_path.exists() else {}
    biome_layout = lexicon.get("biome_layout", {})
    blocks = biome_layout.get("blocks", [])

    if not blocks:
        print("[ERROR] No biome_layout.blocks in lexicon")
        return 1

    # Build grid layout from blocks (sorted by row, then col)
    grid_positions: dict[tuple[int, int], str] = {}
    block_size = biome_layout.get("block_size", 20)
    for block in blocks:
        grid_row = block["rows"][0] // block_size
        grid_col = block["cols"][0] // block_size
        grid_positions[(grid_row, grid_col)] = block["biome"]

    max_row = max(r for r, c in grid_positions)
    max_col = max(c for r, c in grid_positions)
    grid_layout = []
    for r in range(max_row + 1):
        row = []
        for c in range(max_col + 1):
            row.append(grid_positions.get((r, c), ""))
        grid_layout.append(row)

    print(f"[INFO] Grid layout: {len(grid_layout)}x{len(grid_layout[0])}")
    for row in grid_layout:
        print(f"  {row}")
    print()

    # Group tiles by biome
    tiles_by_biome: dict[str, list[dict]] = {}
    for tile in raw.get("tiles", []):
        pos = tile.get("position", [0, 0])
        x, y = int(pos[0]), int(pos[1])
        for block in blocks:
            r, c = block["rows"], block["cols"]
            if r[0] <= x <= r[1] and c[0] <= y <= c[1]:
                tiles_by_biome.setdefault(block["biome"], []).append(tile)
                break

    # Select representatives and build prompts
    output_dir = _PROJECT_ROOT / "assets" / "map_overview" / "shattered_realms"
    output_dir.mkdir(parents=True, exist_ok=True)
    panels: dict[str, Path] = {}

    all_biomes = sorted(set(b["biome"] for b in blocks))
    print(f"[INFO] Generating {len(all_biomes)} biome panels...")
    start = time.time()

    for i, biome_id in enumerate(all_biomes):
        biome_tiles = tiles_by_biome.get(biome_id, [])
        rep = _select_representative(biome_id, biome_tiles, lexicon)
        prompt = _build_biome_map_prompt(biome_id, rep, lexicon)

        panel_path = output_dir / f"panel_{biome_id}.png"
        panels[biome_id] = panel_path

        # Skip if already generated (resume support)
        if panel_path.exists():
            print(f"[{i+1}/{len(all_biomes)}] Skipping {biome_id} — already exists")
            continue

        print(f"[{i+1}/{len(all_biomes)}] Generating {biome_id} (icon: {rep.name})...")
        print(f"  Prompt: {prompt[:120]}...")

        success = generate_biome_panel(biome_id, prompt, panel_path)
        if success:
            print(f"  Saved: {panel_path.name}")
        else:
            print(f"  FAILED: {biome_id}")

        time.sleep(2.0)

    elapsed = time.time() - start
    print(f"\n[INFO] Panels generated in {elapsed:.0f}s")

    # Stitch into final map
    final_path = output_dir / "world_map.png"
    print(f"[INFO] Stitching {len(panels)} panels into {final_path}...")
    stitch_panels(panels, grid_layout, final_path)

    # Write coordinate mapping
    mapping_path = output_dir / "coordinate_mapping.json"
    generate_coordinate_mapping(grid_layout, biome_layout, mapping_path)

    print(f"\n[DONE] World map: {final_path}")
    print(f"       Mapping:   {mapping_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

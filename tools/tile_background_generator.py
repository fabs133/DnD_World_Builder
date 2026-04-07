"""Per-tile background generator for scenario exploration.

Thin wrapper around :mod:`tools.comfyui_batch_generator` that takes a list
of map tiles and produces one unique background image per tile via the
existing ComfyUI pipeline.

Design notes:
- Synchronous and sequential — matches the existing batch generator.
- Deterministic seeds per tile position so re-runs and cancel/resume
  produce stable output.
- Skips tiles whose output file already exists on disk (resume support).
- Output convention: ``assets/tile_backgrounds/{map_slug}/tile_{x}_{y}.png``.

Reuses from :mod:`comfyui_batch_generator`:
    _build_txt2img_workflow, submit_prompt, wait_for_completion,
    get_output_images, copy_output_to_project, _name_to_seed,
    GenerationTask, NEGATIVE_BACKGROUND, PROJECT_ASSETS.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Callable, Iterable

try:
    from tools.comfyui_batch_generator import (
        GenerationTask,
        NEGATIVE_BACKGROUND,
        PROJECT_ASSETS,
        _build_txt2img_workflow,
        _name_to_seed,
        copy_output_to_project,
        get_output_images,
        submit_prompt,
        wait_for_completion,
    )
except ImportError:  # pragma: no cover - used when tools/ is on sys.path directly
    from comfyui_batch_generator import (
        GenerationTask,
        NEGATIVE_BACKGROUND,
        PROJECT_ASSETS,
        _build_txt2img_workflow,
        _name_to_seed,
        copy_output_to_project,
        get_output_images,
        submit_prompt,
        wait_for_completion,
    )


# ── Prompt composition ─────────────────────────────────────────────────

_TERRAIN_PHRASES: dict[str, str] = {
    "grass": "lush grassy field, detailed blades of grass, wildflowers",
    "water": "rippling water surface, reflections, gentle waves",
    "mountain": "rocky mountain terrain, boulders, rugged stone",
    "floor": "worn stone floor, dungeon interior, torch-lit",
    "wall": "ancient stone wall, mossy bricks, weathered",
    "sand": "fine sand dunes, windswept desert, sunlit",
    "swamp": "murky swamp, twisted roots, misty bog",
}

_STYLE_SUFFIX = (
    "fantasy D&D, atmospheric, top-down perspective, masterpiece, "
    "best quality, highly detailed"
)


def _tile_terrain(tile: dict) -> str:
    """Return the lowercase terrain string for a tile dict, defaulting to 'grass'."""
    terrain = tile.get("terrain", "GRASS")
    if isinstance(terrain, str):
        return terrain.lower()
    # Enum fallback
    return getattr(terrain, "value", "grass").lower()


def _tile_zone_label(tile: dict) -> str:
    """Extract a descriptive zone/label string from the tile."""
    zone_id = tile.get("zone_id") or ""
    user_label = tile.get("user_label") or ""
    zones = tile.get("zones") or []
    if zones and isinstance(zones, list):
        first = zones[0]
        if isinstance(first, dict):
            return first.get("label") or first.get("zone_id") or ""
    return user_label or zone_id or ""


def _tile_position(tile: dict) -> tuple[int, int] | None:
    """Return ``(x, y)`` from a tile dict or None if malformed."""
    pos = tile.get("position")
    if not pos or len(pos) < 2:
        return None
    try:
        return int(pos[0]), int(pos[1])
    except (TypeError, ValueError):
        return None


def _own_edge_phrases(tile: dict) -> list[str]:
    """Format this tile's own edge_structures as prompt fragments."""
    phrases: list[str] = []
    for s in tile.get("edge_structures") or []:
        if not isinstance(s, dict):
            continue
        desc = (s.get("description") or "").strip()
        anchor = (s.get("anchor") or "").strip().lower()
        if not desc or anchor not in ("left", "right"):
            continue
        phrases.append(f"{desc} on the {anchor} edge of the frame")
    return phrases


def _inherited_edge_phrases(
    tile: dict,
    tile_index: dict[tuple[int, int], dict],
) -> list[str]:
    """Build phrases for structures that spill in from neighbouring tiles.

    A structure on the LEFT neighbour anchored ``right`` (with propagate)
    continues into the current tile's **left** edge, and vice versa.
    """
    pos = _tile_position(tile)
    if pos is None:
        return []

    x, y = pos
    phrases: list[str] = []

    def _pick(neighbour: dict | None, neighbour_anchor: str, our_edge: str) -> None:
        if not neighbour:
            return
        for s in neighbour.get("edge_structures") or []:
            if not isinstance(s, dict):
                continue
            if (s.get("anchor") or "").strip().lower() != neighbour_anchor:
                continue
            if s.get("propagate", True) is False:
                continue
            desc = (s.get("description") or "").strip()
            if not desc:
                continue
            phrases.append(
                f"continuation of {desc} entering from the {our_edge} edge"
            )

    _pick(tile_index.get((x - 1, y)), neighbour_anchor="right", our_edge="left")
    _pick(tile_index.get((x + 1, y)), neighbour_anchor="left", our_edge="right")
    return phrases


def build_tile_prompt(
    tile: dict,
    biome_hint: str = "",
    tile_index: dict[tuple[int, int], dict] | None = None,
    lexicon: dict | None = None,
):
    """Compose a ComfyUI prompt for a tile, routed by tile type.

    Returns either a ``str`` (flat prompt for transit/riddle tiles) or a
    :class:`~tools.regional_workflow.RegionalPrompt` (structured prompt
    for narrative/boss/pack tiles that need spatial separation).

    :param tile: Tile dict.
    :param biome_hint: Shared biome descriptor.
    :param tile_index: Optional ``{(x, y): tile_dict}`` for edge-
        structure continuity.
    :param lexicon: Optional biome lexicon dict for thematic variety.
    """
    try:
        from tools.tile_classifier import classify_tile
        from tools.tile_prompt_builders import BUILDERS
        from tools.regional_workflow import RegionalPrompt
    except ImportError:  # pragma: no cover
        from tile_classifier import classify_tile  # type: ignore
        from tile_prompt_builders import BUILDERS  # type: ignore
        from regional_workflow import RegionalPrompt  # type: ignore

    tile_type = classify_tile(tile)
    builder = BUILDERS.get(tile_type, BUILDERS["transit"])
    result = builder(tile, lexicon or {}, biome_hint)

    # Collect edge-structure phrases that apply regardless of tile type.
    edge_parts = list(_own_edge_phrases(tile))
    if tile_index is not None:
        edge_parts.extend(_inherited_edge_phrases(tile, tile_index))

    if isinstance(result, RegionalPrompt):
        # Append edge structures to the base conditioning so they're
        # visible in the whole image without interfering with regions.
        if edge_parts:
            result.base += ", " + ", ".join(edge_parts)
        return result

    # Flat prompt path (transit / riddle)
    parts: list[str] = list(result)
    parts.extend(edge_parts)
    parts.append(_STYLE_SUFFIX)
    return ", ".join(p for p in parts if p)


# ── Map slug ───────────────────────────────────────────────────────────


def map_slug(map_name: str) -> str:
    """Convert a map name to a filesystem-safe slug."""
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", map_name).strip("_").lower()
    return slug or "map"


def tile_output_path(map_slug_str: str, x: int, y: int) -> Path:
    """Return the absolute output path for a tile's background image.

    Ensures the parent directory exists.
    """
    path = PROJECT_ASSETS / "tile_backgrounds" / map_slug_str / f"tile_{x}_{y}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def tile_relative_path(map_slug_str: str, x: int, y: int) -> str:
    """Return the project-relative path string stored in ``tile.background_image``."""
    return f"assets/tile_backgrounds/{map_slug_str}/tile_{x}_{y}.png"


# ── Generation ─────────────────────────────────────────────────────────


# Legacy constant kept for backward compatibility with imports from
# tile_prompt_builders.py. Reads from the active model profile.
def _get_negative_people() -> str:
    try:
        from tools.model_profile import get_active_profile
    except ImportError:  # pragma: no cover
        from model_profile import get_active_profile  # type: ignore
    return get_active_profile().negative_people

# Expose as a module-level string for importers that read it at import time.
# (tile_prompt_builders does ``from ... import _NEGATIVE_PEOPLE_BACKGROUND``)
_NEGATIVE_PEOPLE_BACKGROUND = _get_negative_people()

# Tile types that depict one or more characters — these get the
# anatomy-focused negative and a higher resolution to give SD 1.5
# enough pixels per face/figure.
_PEOPLE_TILE_TYPES = frozenset({"narrative", "boss", "pack"})


def _has_people(tile: dict) -> bool:
    """True if the tile's classified type involves rendering figures."""
    try:
        from tools.tile_classifier import classify_tile
    except ImportError:  # pragma: no cover
        from tile_classifier import classify_tile  # type: ignore
    return classify_tile(tile) in _PEOPLE_TILE_TYPES


def _build_task(
    tile: dict,
    slug: str,
    biome_hint: str,
    tile_index: dict[tuple[int, int], dict] | None = None,
    lexicon: dict | None = None,
) -> tuple:
    """Create a GenerationTask for one tile.

    Returns ``(task, regional_prompt_or_None)``. When the prompt composer
    returns a :class:`~tools.regional_workflow.RegionalPrompt`, the
    caller must use :func:`build_regional_workflow` instead of the flat
    txt2img workflow.
    """
    try:
        from tools.regional_workflow import RegionalPrompt
    except ImportError:  # pragma: no cover
        from regional_workflow import RegionalPrompt  # type: ignore

    pos = tile.get("position", [0, 0])
    x, y = int(pos[0]), int(pos[1])

    prompt_result = build_tile_prompt(
        tile, biome_hint, tile_index=tile_index, lexicon=lexicon,
    )
    seed_key = f"{slug}_{x}_{y}"

    try:
        from tools.model_profile import get_active_profile
    except ImportError:  # pragma: no cover
        from model_profile import get_active_profile  # type: ignore
    profile = get_active_profile()

    regional = None
    if isinstance(prompt_result, RegionalPrompt):
        regional = prompt_result
        prompt_str = regional.base
        negative = regional.negative
        width, height = profile.people_resolution
        steps = profile.steps_people
        cfg = profile.cfg_people
    elif _has_people(tile):
        prompt_str = prompt_result
        negative = profile.negative_people
        width, height = profile.people_resolution
        steps = profile.steps_people
        cfg = profile.cfg_people
    else:
        prompt_str = prompt_result
        negative = profile.negative_scenery
        width, height = profile.base_resolution
        steps = profile.steps_scenery
        cfg = profile.cfg_scenery

    # Update regional dimensions to match profile
    if regional is not None:
        regional.width, regional.height = width, height

    task = GenerationTask(
        task_type="background",
        entity_name=f"tile_{x}_{y}",
        prompt=prompt_str,
        negative=negative,
        output_path=tile_relative_path(slug, x, y),
        seed=_name_to_seed(seed_key, offset=9000),
        steps=steps,
        cfg=cfg,
        width=width,
        height=height,
        checkpoint=profile.checkpoint,
        vae=profile.vae or profile.checkpoint,
    )
    return task, regional


def generate_tile_backgrounds(
    tiles: Iterable[dict],
    map_name: str,
    on_progress: Callable[[int, int, str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
    biome_hint: str = "",
    pause_between: float = 2.0,
    lexicon: dict | None = None,
) -> dict[tuple[int, int], str]:
    """Generate one background image per tile via ComfyUI.

    :param tiles: Iterable of tile dicts (each must have ``position`` and
        ``terrain`` keys).
    :param map_name: Display name of the map; used to form a filesystem slug.
    :param on_progress: Optional callback ``(done, total, status)`` called
        after each tile (and once before the first).
    :param cancel_check: Optional callable returning True to abort the loop
        between tiles. Completed tiles are preserved.
    :param biome_hint: Optional free-form biome string (e.g. "dark forest")
        prepended to every prompt for stylistic consistency.
    :param pause_between: Seconds to sleep between successive ComfyUI
        submissions (matches the batch generator's default).
    :param lexicon: Optional biome lexicon used by the prompt builders
        for thematic variety. See
        :func:`tile_prompt_builders.build_narrative_phrases` et al.

    :returns: ``{(x, y): relative_output_path}`` for every tile that now
        has a valid output on disk (including pre-existing files).
    """
    tile_list = list(tiles)
    total = len(tile_list)
    slug = map_slug(map_name)
    results: dict[tuple[int, int], str] = {}

    # Build a (x, y) → tile index so the prompt composer can pull in
    # structures from neighbouring tiles for visual continuity.
    tile_index: dict[tuple[int, int], dict] = {}
    for t in tile_list:
        p = _tile_position(t)
        if p is not None:
            tile_index[p] = t

    def _progress(done: int, status: str) -> None:
        if on_progress is not None:
            on_progress(done, total, status)

    _progress(0, "Starting…")

    for idx, tile in enumerate(tile_list):
        if cancel_check and cancel_check():
            _progress(idx, "Cancelled")
            break

        pos = tile.get("position", [0, 0])
        x, y = int(pos[0]), int(pos[1])

        out_abs = tile_output_path(slug, x, y)
        rel_path = tile_relative_path(slug, x, y)

        # Resume support: skip if already present.
        if out_abs.exists():
            results[(x, y)] = rel_path
            _progress(idx + 1, f"Skipped tile ({x}, {y}) — already exists")
            continue

        _progress(idx, f"Generating tile ({x}, {y})…")

        task, regional = _build_task(
            tile, slug, biome_hint,
            tile_index=tile_index, lexicon=lexicon,
        )

        mask_files: list[str] = []
        if regional is not None:
            try:
                from tools.regional_workflow import (
                    build_regional_workflow, cleanup_masks,
                )
            except ImportError:  # pragma: no cover
                from regional_workflow import (  # type: ignore
                    build_regional_workflow, cleanup_masks,
                )
            workflow, mask_files = build_regional_workflow(task, regional)
        else:
            workflow = _build_txt2img_workflow(task)

        try:
            prompt_id = submit_prompt(workflow)
            if not prompt_id:
                _progress(idx + 1, f"Submit failed for tile ({x}, {y})")
                continue

            history = wait_for_completion(prompt_id, timeout=180)
            if not history:
                _progress(idx + 1, f"Timeout on tile ({x}, {y})")
                continue

            images = get_output_images(history)
            if not images:
                _progress(idx + 1, f"No output for tile ({x}, {y})")
                continue

            # ComfyUI adds suffixes like _00001.png — use the first image.
            if copy_output_to_project(images[0]["filename"], rel_path):
                results[(x, y)] = rel_path
                _progress(idx + 1, f"Saved tile ({x}, {y})")
            else:
                _progress(idx + 1, f"Copy failed for tile ({x}, {y})")
        finally:
            # Clean up temporary mask PNGs from ComfyUI's input/ directory.
            if mask_files:
                try:
                    from tools.regional_workflow import cleanup_masks
                except ImportError:  # pragma: no cover
                    from regional_workflow import cleanup_masks  # type: ignore
                cleanup_masks(mask_files)

        # Throttle between submissions to avoid hammering ComfyUI.
        if idx < total - 1 and pause_between > 0:
            time.sleep(pause_between)

    return results

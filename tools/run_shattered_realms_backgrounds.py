"""Generate a classifier-enriched background for every tile in
``workspace/shattered_realms/map.json``.

This is the "production" runner for the tile background pipeline. It:

1. Loads the biome lexicon sidecar at
   ``workspace/shattered_realms/biome_lexicon.json`` — the file also
   carries a ``biome_layout`` section mapping grid blocks to biome IDs.
2. Derives a biome key for every tile from its grid position via the
   layout (robust against background_image edits from prior runs).
3. Groups tiles by biome so each group gets a consistent biome hint.
4. Invokes :func:`tile_background_generator.generate_tile_backgrounds`
   with the lexicon, letting the classifier + per-type prompt builders
   do the heavy lifting.
5. Checkpoints ``map.json`` every ``_CHECKPOINT_EVERY`` tiles so the
   job can be stopped and resumed without losing progress.
6. Logs the classified type distribution at the end of the run.

Usage::

    python tools/run_shattered_realms_backgrounds.py

Environment:
    COMFYUI_API     (default http://127.0.0.1:8000)
    COMFYUI_OUTPUT_DIR
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

# Resolve project imports from the tools/ subdirectory.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tools.tile_background_generator import (  # noqa: E402
    generate_tile_backgrounds,
    map_slug,
)
from tools.tile_classifier import classify_tile  # noqa: E402


_MAP_PATH = _PROJECT_ROOT / "workspace" / "shattered_realms" / "map.json"
_LEXICON_PATH = _PROJECT_ROOT / "workspace" / "shattered_realms" / "biome_lexicon.json"
_LOG_PATH = _PROJECT_ROOT / "workspace" / "shattered_realms" / "bg_generation.log"
_CHECKPOINT_EVERY = 25


# ── Lexicon loading ───────────────────────────────────────────────────


def _load_lexicon() -> dict:
    if not _LEXICON_PATH.exists():
        print(f"[WARN] No lexicon found at {_LEXICON_PATH} — running without biome flavor")
        return {}
    try:
        return json.loads(_LEXICON_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[WARN] Failed to load lexicon: {exc}")
        return {}


def _biome_for_position(
    x: int,
    y: int,
    layout: dict | None,
) -> str:
    """Return the biome ID that contains the ``(x, y)`` grid position,
    or an empty string if no layout is available."""
    if not layout:
        return ""
    for block in layout.get("blocks") or []:
        rows = block.get("rows") or []
        cols = block.get("cols") or []
        if len(rows) != 2 or len(cols) != 2:
            continue
        if rows[0] <= x <= rows[1] and cols[0] <= y <= cols[1]:
            return block.get("biome", "")
    return ""


def _humanize_biome(biome_id: str) -> str:
    """Turn ``dark_forest`` into ``dark forest`` for prompt prefixes."""
    return biome_id.replace("_", " ").strip()


# ── Main ──────────────────────────────────────────────────────────────


def main() -> int:
    if not _MAP_PATH.exists():
        print(f"[ERROR] map.json not found at {_MAP_PATH}")
        return 1

    raw = json.loads(_MAP_PATH.read_text(encoding="utf-8"))
    tiles: list[dict] = raw.get("tiles", [])
    total = len(tiles)
    slug = map_slug("shattered_realms")

    lexicon = _load_lexicon()
    biome_layout = lexicon.get("biome_layout") if lexicon else None
    if biome_layout:
        print(
            f"[INFO] Loaded biome layout with "
            f"{len(biome_layout.get('blocks', []))} blocks"
        )
    else:
        print("[WARN] No biome layout in lexicon — falling back to background_image")

    print(f"[INFO] Loaded {total} tiles from {_MAP_PATH}")
    print(f"[INFO] Output: assets/tile_backgrounds/{slug}/")
    print(f"[INFO] Log:    {_LOG_PATH}")
    print(f"[INFO] Checkpoint every {_CHECKPOINT_EVERY} tiles")
    print(f"[INFO] Started at {datetime.now().isoformat(timespec='seconds')}")
    print()

    # ── Pre-classify every tile and group by biome ───────────────────
    type_counts: Counter = Counter()
    groups: dict[str, list[dict]] = {}
    for tile in tiles:
        pos = tile.get("position", [0, 0])
        x, y = int(pos[0]), int(pos[1])
        biome_id = _biome_for_position(x, y, biome_layout)
        if not biome_id:
            # Fallback: try deriving from the existing background_image
            bg = tile.get("background_image") or ""
            if bg and "assets/backgrounds/" in bg:
                biome_id = Path(bg).stem

        # Stamp the biome key directly on the tile dict so prompt
        # builders can look it up regardless of what the (possibly
        # already-edited) background_image field contains.
        if biome_id:
            tile["biome_key"] = biome_id

        groups.setdefault(biome_id, []).append(tile)
        type_counts[classify_tile(tile)] += 1

    print("[INFO] Tile type distribution (via classifier):")
    for ttype, count in type_counts.most_common():
        pct = 100 * count / max(total, 1)
        print(f"         {ttype:12s} {count:5d}  ({pct:5.1f}%)")
    print()

    print(f"[INFO] Biome groups: {len(groups)}")
    for biome_id, group in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        label = biome_id or "(unknown)"
        print(f"         {label:25s} {len(group):5d} tiles")
    print()

    done_count = 0
    start_time = time.time()
    log_file = _LOG_PATH.open("a", encoding="utf-8")
    log_file.write(
        f"\n=== Run started {datetime.now().isoformat(timespec='seconds')} ===\n"
    )
    log_file.write(
        f"Type distribution: {dict(type_counts)}\n"
    )
    log_file.flush()

    def save_checkpoint() -> None:
        # biome_key is an in-memory hint for the prompt builders — never
        # persist it to disk (it would leak a runtime field into map.json).
        for t in raw.get("tiles", []):
            t.pop("biome_key", None)
        _MAP_PATH.write_text(
            json.dumps(raw, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        # Restore the hint after writing so later generation loops still
        # have it available.
        for t in raw.get("tiles", []):
            pos = t.get("position", [0, 0])
            bid = _biome_for_position(int(pos[0]), int(pos[1]), biome_layout)
            if bid:
                t["biome_key"] = bid

    try:
        for biome_id, group in groups.items():
            biome_hint = _humanize_biome(biome_id) or ""
            label = biome_id or "(no biome)"
            print(f"[BIOME] {label}  ({len(group)} tiles, hint={biome_hint!r})")
            log_file.write(f"[BIOME] {label} - {len(group)} tiles\n")
            log_file.flush()

            pos_to_tile: dict[tuple[int, int], dict] = {}
            for t in group:
                p = t.get("position", [0, 0])
                pos_to_tile[(int(p[0]), int(p[1]))] = t

            def on_progress(done: int, total_in_group: int, status: str) -> None:
                nonlocal done_count
                elapsed = time.time() - start_time
                rate = done_count / elapsed if elapsed > 0 else 0
                remaining = (total - done_count) / rate if rate > 0 else -1
                line = (
                    f"[{done_count:4d}/{total}] {status}  "
                    f"(group {done}/{total_in_group}, "
                    f"~{remaining/3600:.1f}h left)"
                )
                print(line)
                log_file.write(line + "\n")
                log_file.flush()

            results = generate_tile_backgrounds(
                tiles=group,
                map_name="shattered_realms",
                on_progress=on_progress,
                biome_hint=biome_hint,
                lexicon=lexicon,
            )

            # Write results back into the raw map dict and checkpoint
            for (x, y), rel_path in results.items():
                tile = pos_to_tile.get((x, y))
                if tile is not None:
                    tile["background_image"] = rel_path
                    done_count += 1
                    if done_count % _CHECKPOINT_EVERY == 0:
                        save_checkpoint()
                        log_file.write(
                            f"[CHECKPOINT] Saved after {done_count} tiles\n"
                        )
                        log_file.flush()

        save_checkpoint()

    except KeyboardInterrupt:
        print("\n[INTERRUPT] Saving checkpoint before exit...")
        save_checkpoint()
        log_file.write(
            f"[INTERRUPT] at {datetime.now().isoformat(timespec='seconds')} "
            f"after {done_count} tiles\n"
        )
        log_file.close()
        return 130

    elapsed = time.time() - start_time
    print()
    print(f"[DONE] Completed {done_count}/{total} tiles in "
          f"{elapsed/3600:.2f} hours")
    log_file.write(
        f"[DONE] {done_count}/{total} in {elapsed/3600:.2f}h "
        f"at {datetime.now().isoformat(timespec='seconds')}\n"
    )
    log_file.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

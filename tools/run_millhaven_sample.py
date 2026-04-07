"""One-off quality-check runner for the enriched tile background pipeline.

Generates a small sample of Millhaven (the beginner village) tiles:
- All 9 narrative tiles (where the storytelling lift matters most)
- 6 transit tiles around them (to see biome flavor in action)

Total: 15 tiles. On an RTX 3060 Ti this runs in roughly 5 minutes and
lets you eyeball the quality before committing to a full overnight run.

Output files land in the same ``assets/tile_backgrounds/shattered_realms/``
directory so you can compare side by side with the old run's outputs.

Usage:
    python tools/run_millhaven_sample.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tools.tile_background_generator import generate_tile_backgrounds  # noqa: E402
from tools.tile_classifier import classify_tile  # noqa: E402


_MAP_PATH = _PROJECT_ROOT / "workspace" / "shattered_realms" / "map.json"
_LEXICON_PATH = (
    _PROJECT_ROOT / "workspace" / "shattered_realms" / "biome_lexicon.json"
)
_OUTPUT_DIR = (
    _PROJECT_ROOT / "assets" / "tile_backgrounds" / "shattered_realms"
)


def main() -> int:
    raw = json.loads(_MAP_PATH.read_text(encoding="utf-8"))
    lexicon = json.loads(_LEXICON_PATH.read_text(encoding="utf-8"))

    # Millhaven: rows 40-59, cols 0-19
    millhaven_tiles = [
        t for t in raw["tiles"]
        if 40 <= t.get("position", [0, 0])[0] <= 59
        and 0 <= t.get("position", [0, 0])[1] <= 19
    ]

    narratives = [t for t in millhaven_tiles if classify_tile(t) == "narrative"]
    transits = [t for t in millhaven_tiles if classify_tile(t) == "transit"]

    # Pick 6 transit tiles scattered across the biome block for variety
    # (deterministic: first, last, and four from the middle evenly spaced).
    if len(transits) >= 6:
        step = max(1, len(transits) // 6)
        transit_picks = [transits[i * step] for i in range(6)]
    else:
        transit_picks = transits[:6]

    # Mark each pick with biome_key so the builders see "millhaven".
    # Also delete any pre-existing output so we truly regenerate.
    picks = narratives + transit_picks
    for t in picks:
        t["biome_key"] = "millhaven"
        pos = t.get("position", [0, 0])
        x, y = int(pos[0]), int(pos[1])
        out_file = _OUTPUT_DIR / f"tile_{x}_{y}.png"
        if out_file.exists():
            out_file.unlink()  # force regeneration for the quality check

    print(f"[INFO] Generating {len(picks)} Millhaven sample tiles")
    print(f"         narrative: {len(narratives)}")
    print(f"         transit:   {len(transit_picks)}")
    print(f"[INFO] Started at {datetime.now().isoformat(timespec='seconds')}")
    print()

    def on_progress(done, total, status):
        print(f"[{done:2d}/{total}] {status}")

    start = time.time()
    results = generate_tile_backgrounds(
        tiles=picks,
        map_name="shattered_realms",
        on_progress=on_progress,
        biome_hint="millhaven",
        lexicon=lexicon,
    )
    elapsed = time.time() - start

    print()
    print(f"[DONE] Generated {len(results)} files in {elapsed:.0f}s "
          f"(avg {elapsed/max(len(results),1):.1f}s/tile)")
    print("[INFO] Sample output files:")
    for (x, y), rel in sorted(results.items()):
        print(f"         assets/tile_backgrounds/shattered_realms/tile_{x}_{y}.png")

    return 0


if __name__ == "__main__":
    sys.exit(main())

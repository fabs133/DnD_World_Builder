#!/usr/bin/env python3
"""Seed empty tiles with terrain-matched side events from the registry."""

import argparse
import json
import random
import sys
from collections import deque
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models.side_events import SIDE_EVENTS, is_terrain_compatible


def seed_events(map_path: Path, coverage: float = 0.35, seed: int = 42,
                dry_run: bool = False) -> dict:
    """Assign side events to empty tiles.

    Returns a stats dict with counts.
    """
    data = json.loads(map_path.read_text(encoding="utf-8"))
    tiles = data.get("tiles", [])

    rng = random.Random(seed)
    recent: deque[int] = deque(maxlen=10)

    stats = {
        "total": len(tiles),
        "empty": 0,
        "eligible": 0,
        "seeded": 0,
        "skipped_quiet": 0,
        "skipped_no_match": 0,
        "by_category": {},
        "by_terrain": {},
    }

    for tile in sorted(tiles, key=lambda t: tuple(t["position"])):
        # Only target truly empty tiles
        if tile.get("entities"):
            continue
        # Note: tiles with triggers are still eligible — triggers are
        # event-bus reactions, not player-facing interactions.
        terrain = tile.get("terrain", "FLOOR").upper()
        if terrain == "WALL":
            continue
        # Already has a side event (re-run safety)
        if tile.get("side_event"):
            continue

        stats["empty"] += 1

        # Coverage roll
        if rng.random() >= coverage:
            stats["skipped_quiet"] += 1
            continue

        stats["eligible"] += 1

        # Build candidate pool
        candidates = [
            e for e in SIDE_EVENTS.values()
            if is_terrain_compatible(e, terrain)
            and e.event_id not in recent
        ]
        if not candidates:
            # Relax recent-avoidance if needed
            candidates = [
                e for e in SIDE_EVENTS.values()
                if is_terrain_compatible(e, terrain)
            ]
        if not candidates:
            stats["skipped_no_match"] += 1
            continue

        event = rng.choice(candidates)
        variant_idx = rng.randint(0, len(event.variants) - 1)

        tile["side_event"] = {"event_id": event.event_id, "variant": variant_idx}
        recent.append(event.event_id)

        stats["seeded"] += 1
        stats["by_category"][event.category] = stats["by_category"].get(event.category, 0) + 1
        stats["by_terrain"][terrain] = stats["by_terrain"].get(terrain, 0) + 1

    if not dry_run:
        map_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Seed empty tiles with side events")
    parser.add_argument("map_path", type=Path, help="Path to map.json")
    parser.add_argument("--coverage", type=float, default=0.35,
                        help="Fraction of empty tiles to seed (default: 0.35)")
    parser.add_argument("--seed", type=int, default=42,
                        help="RNG seed for deterministic assignment (default: 42)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show stats without modifying the file")
    args = parser.parse_args()

    if not args.map_path.exists():
        print(f"ERROR: {args.map_path} not found")
        return

    mode = "[DRY RUN] " if args.dry_run else ""
    print(f"{mode}Seeding side events in {args.map_path}")
    print(f"  Coverage: {args.coverage:.0%}  Seed: {args.seed}")

    stats = seed_events(args.map_path, args.coverage, args.seed, args.dry_run)

    print(f"\nResults:")
    print(f"  Total tiles:     {stats['total']}")
    print(f"  Empty tiles:     {stats['empty']}")
    print(f"  Seeded:          {stats['seeded']}")
    print(f"  Quiet (no event):{stats['skipped_quiet']}")
    print(f"  No terrain match:{stats['skipped_no_match']}")
    print(f"\n  By category:")
    for cat, count in sorted(stats["by_category"].items()):
        print(f"    {cat:15s}: {count}")
    print(f"\n  By terrain:")
    for ter, count in sorted(stats["by_terrain"].items()):
        print(f"    {ter:10s}: {count}")


if __name__ == "__main__":
    main()

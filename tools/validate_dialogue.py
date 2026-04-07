#!/usr/bin/env python3
"""Validate NPC dialogue graphs in a scenario map.json.

Reads all entities with dialogue data, builds/converts graphs,
and runs structural validation checks.

Usage:
    python tools/validate_dialogue.py workspace/shattered_realms/map.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/validate_dialogue.py <map.json>")
        sys.exit(1)

    map_path = Path(sys.argv[1])
    data = json.loads(map_path.read_text(encoding="utf-8"))

    from models.dialogue.dialogue_graph import DialogueGraph

    total = 0
    valid = 0
    errors_total = 0

    for tile in data.get("tiles", []):
        for e in tile.get("entities", []):
            graph_data = e.get("dialogue_graph")
            dialogue_lines = e.get("dialogue_lines")
            if not graph_data and not dialogue_lines:
                continue

            name = e.get("name", "?")
            total += 1

            if graph_data:
                graph = DialogueGraph.from_dict(graph_data)
                source = "explicit graph"
            else:
                graph = DialogueGraph.from_dialogue_lines(dialogue_lines)
                source = "auto-converted"

            errors = graph.validate()
            if errors:
                print(f"  FAIL  {name} ({source}, {len(graph.nodes)} nodes)")
                for err in errors:
                    print(f"        - {err}")
                errors_total += len(errors)
            else:
                valid += 1
                print(f"  OK    {name} ({source}, {len(graph.nodes)} nodes)")

    print(f"\n{valid}/{total} valid, {errors_total} errors")
    sys.exit(0 if errors_total == 0 else 1)


if __name__ == "__main__":
    main()

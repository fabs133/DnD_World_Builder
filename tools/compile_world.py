#!/usr/bin/env python3
"""Compile biome YAML files into a playable map.json for the workspace.

Reads the world YAML + all referenced biome YAMLs, and produces a single
map.json that the game's play session can load.

Usage:
    python tools/compile_world.py scenarios/world_shattered_realms.yaml
    python tools/compile_world.py scenarios/world_shattered_realms.yaml --output workspace/shattered_realms
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. pip install pyyaml")
    sys.exit(1)


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def build_entity_dict(entity_cfg: dict) -> dict:
    """Convert a biome YAML entity into a map.json entity dict."""
    stats = entity_cfg.get("stats", {})
    hp = stats.get("hp", 10)
    max_hp = stats.get("max_hp", hp)

    result = {
        "name": entity_cfg["name"],
        "entity_type": entity_cfg.get("entity_type", "enemy"),
        "stats": stats,
        "inventory": entity_cfg.get("inventory", []),
        "triggers": [],
        "hp": hp,
        "max_hp": max_hp,
        "conditions": [],
    }

    # Portrait paths
    portraits_cfg = entity_cfg.get("portraits", {})
    if isinstance(portraits_cfg, dict) and portraits_cfg.get("needed"):
        portraits = {}
        for state, state_data in portraits_cfg.get("health_states", {}).items():
            if isinstance(state_data, dict) and state_data.get("output"):
                portraits[state] = state_data["output"]
        if portraits:
            result["portraits"] = portraits
            if "healthy" in portraits:
                result["image_path"] = portraits["healthy"]

    # Voice profile
    voice = entity_cfg.get("voice")
    if voice and isinstance(voice, dict):
        preset_name = voice.get("preset", "")
        try:
            from core.voice.voice_profile import VoiceProfile
            vid = VoiceProfile.deterministic_voice_id(entity_cfg["name"], preset_name)
        except ImportError:
            import hashlib
            vid = hashlib.sha256(f"{entity_cfg['name']}|{preset_name}".encode()).hexdigest()[:12]
        result["voice_profile"] = {
            "voice_id": vid,
            "source_type": "preset",
            "preset_name": preset_name,
            "reference_audio": voice.get("reference_audio", ""),
            "exaggeration": voice.get("exaggeration", 0.5),
            "speed_factor": voice.get("speed", 1.0),
            "cfg_weight": voice.get("cfg_weight", 0.5),
        }

    # Voice line output paths
    voice_lines_cfg = entity_cfg.get("voice_lines", {})
    if voice_lines_cfg.get("needed") and voice_lines_cfg.get("output_dir"):
        result["voice_lines_dir"] = voice_lines_cfg["output_dir"]

    # Dialogue lines
    dialogue = entity_cfg.get("dialogue")
    if dialogue and isinstance(dialogue, dict):
        result["dialogue_lines"] = dialogue

    return result


def _build_condition(condition_cfg: dict) -> dict:
    """Build a condition dict matching the game's Trigger.from_dict format."""
    ctype = condition_cfg.get("type", "AlwaysTrue")
    args = dict(condition_cfg)  # copy all fields
    args["type"] = ctype  # ensure type is in args (game expects it)
    return {"type": ctype, "args": args}


def _build_reaction(reaction_cfg: dict) -> dict:
    """Build a reaction dict matching the game's Trigger.from_dict format."""
    rtype = reaction_cfg.get("type", "AlertGamemaster")
    raw_args = dict(reaction_cfg.get("args", {}))
    raw_args["type"] = rtype  # game expects type inside args

    # Normalize key names to match game's from_dict expectations
    if rtype == "ApplyDamage":
        # YAML uses "damage", game expects "amount"
        if "damage" in raw_args and "amount" not in raw_args:
            raw_args["amount"] = raw_args.pop("damage")

    return {"type": rtype, "args": raw_args}


def _build_single_trigger(trigger_cfg: dict) -> dict:
    """Build one trigger dict (no recursion for next_trigger)."""
    return {
        "event_type": trigger_cfg.get("event_type", "ENTER_TILE"),
        "label": trigger_cfg.get("label", ""),
        "condition": _build_condition(trigger_cfg.get("condition", {})),
        "reaction": _build_reaction(trigger_cfg.get("reaction", {})),
        "next_trigger": None,
    }


def build_trigger_dict(trigger_cfg: dict) -> dict:
    """Convert a biome YAML trigger into a map.json trigger dict."""
    result = _build_single_trigger(trigger_cfg)

    # Nested next_trigger
    next_t = trigger_cfg.get("next_trigger")
    if next_t:
        result["next_trigger"] = _build_single_trigger(next_t)

    return result


def compile_world(world_path: Path) -> dict:
    """Compile world + biome YAMLs into a map.json dict."""
    world = load_yaml(world_path)
    world_cfg = world.get("world", {})
    base_dir = world_path.parent

    block_size = world_cfg.get("block_size", [20, 20])
    grid_size = world_cfg.get("grid_size", [3, 3])
    total_rows = grid_size[0] * block_size[0]
    total_cols = grid_size[1] * block_size[1]

    # Initialize all tiles with default terrain
    tiles: dict[tuple[int, int], dict] = {}
    for r in range(total_rows):
        for c in range(total_cols):
            tiles[(r, c)] = {
                "tile_id": f"{r}_{c}",
                "position": [r, c],
                "terrain": "GRASS",
                "tags": [],
                "user_label": None,
                "note": None,
                "overlay_color": None,
                "last_updated": None,
                "entities": [],
                "triggers": [],
            }

    all_quests: list[dict] = []

    # Process each biome
    biome_files = world_cfg.get("biome_files", {})
    for biome_id, filename in biome_files.items():
        biome_path = base_dir / filename
        if not biome_path.exists():
            print(f"  [SKIP] {filename} not found")
            continue

        print(f"  Loading biome: {biome_id} from {filename}")
        biome_data = load_yaml(biome_path)
        biome_cfg = biome_data.get("biome", {})

        offset = biome_cfg.get("grid_offset", [0, 0])
        default_terrain = biome_cfg.get("terrain_default", "GRASS")
        brows, bcols = block_size

        default_ambient = biome_cfg.get("ambient_audio", "")

        # Biome-level background image (far layer)
        biome_bg = biome_cfg.get("assets", {}).get("background", {}).get("output", "")

        # Set default terrain, ambient, and biome background for this block
        for lr in range(brows):
            for lc in range(bcols):
                wr, wc = lr + offset[0], lc + offset[1]
                if (wr, wc) in tiles:
                    tiles[(wr, wc)]["terrain"] = default_terrain
                    if default_ambient:
                        tiles[(wr, wc)]["ambient_audio"] = default_ambient
                    if biome_bg:
                        tiles[(wr, wc)]["background_image"] = biome_bg

        # Build zone lookup: tile position → zone label
        zone_tiles: dict[tuple[int, int], str] = {}
        zone_descriptions: dict[str, str] = {}
        biome_zones = biome_data.get("zones", [])
        zone_ids = [z.get("id", "") for z in biome_zones]

        for zone in biome_zones:
            zone_id = zone.get("id", "")
            label = zone.get("label", "")
            desc = zone.get("description", "")
            zone_descriptions[zone_id] = desc
            for t in zone.get("tiles", []):
                pos = (t[0] + offset[0], t[1] + offset[1])
                zone_tiles[pos] = label

            # Set zone terrain if different from default
            zone_terrain = zone.get("terrain")
            if zone_terrain and zone_terrain != default_terrain:
                for t in zone.get("tiles", []):
                    wr, wc = t[0] + offset[0], t[1] + offset[1]
                    if (wr, wc) in tiles:
                        tiles[(wr, wc)]["terrain"] = zone_terrain

            # Set zone ambient audio override
            zone_ambient = zone.get("ambient_audio")
            if zone_ambient:
                for t in zone.get("tiles", []):
                    wr, wc = t[0] + offset[0], t[1] + offset[1]
                    if (wr, wc) in tiles:
                        tiles[(wr, wc)]["ambient_audio"] = zone_ambient

            # Build zone background path
            zone_bg = zone.get("background", {})
            bg_path = zone_bg.get("output") if zone_bg else None

            # Build connections to other zones in this biome
            connections = [z for z in zone_ids if z != zone_id]

            # Build TileZone-compatible dict for this zone
            zone_dict = {
                "zone_id": zone_id,
                "label": label,
                "description": desc,
                "background_image": bg_path,
                "connections": connections,
                "locked": False,
                "lock_dc": 15,
                "tags": zone.get("tags", []),
            }

            # Attach zone dict to every tile in this zone
            for t in zone.get("tiles", []):
                wr, wc = t[0] + offset[0], t[1] + offset[1]
                if (wr, wc) in tiles:
                    if "zones" not in tiles[(wr, wc)]:
                        tiles[(wr, wc)]["zones"] = []
                    tiles[(wr, wc)]["zones"].append(zone_dict)

        # Also attach sibling zones so navigation works within a tile
        # Each tile gets all zones from its biome that share any tile
        # (already handled above — connections list covers navigation)

        # Apply zone labels to tiles
        for pos, label in zone_tiles.items():
            if pos in tiles:
                tiles[pos]["user_label"] = label

        # Terrain overrides
        for override in biome_data.get("terrain_overrides", []):
            terrain = override.get("terrain", "GRASS")
            overlay = override.get("overlay_color")
            for t in override.get("tiles", []):
                wr, wc = t[0] + offset[0], t[1] + offset[1]
                if (wr, wc) in tiles:
                    tiles[(wr, wc)]["terrain"] = terrain
                    if overlay:
                        tiles[(wr, wc)]["overlay_color"] = overlay

        # Place entities
        for entity_cfg in biome_data.get("entities", []):
            positions = entity_cfg.get("position", [])
            count = entity_cfg.get("count", 1)
            entity_dict = build_entity_dict(entity_cfg)

            for i, pos in enumerate(positions):
                if i >= count:
                    break
                wr, wc = pos[0] + offset[0], pos[1] + offset[1]
                if (wr, wc) in tiles:
                    tiles[(wr, wc)]["entities"].append(dict(entity_dict))

        # Collect quests
        for quest_cfg in biome_data.get("quests", []):
            all_quests.append({
                "id": quest_cfg.get("id", ""),
                "name": quest_cfg.get("name", ""),
                "type": quest_cfg.get("type", "side"),
                "giver": quest_cfg.get("giver"),
                "zone": quest_cfg.get("zone", ""),
                "biome": biome_id,
                "description": quest_cfg.get("description", ""),
                "objectives": quest_cfg.get("objectives", []),
                "reward": quest_cfg.get("reward", {}),
                "difficulty": quest_cfg.get("difficulty", 1),
            })

        # Place triggers
        for trigger_cfg in biome_data.get("triggers", []):
            tile_pos = trigger_cfg.get("tile", [])
            if not tile_pos or not isinstance(tile_pos, list) or len(tile_pos) < 2:
                continue
            wr, wc = tile_pos[0] + offset[0], tile_pos[1] + offset[1]
            if (wr, wc) in tiles:
                tiles[(wr, wc)]["triggers"].append(build_trigger_dict(trigger_cfg))

    # Place player entities at spawn location
    players_cfg = world.get("players", {})
    spawn_biome = players_cfg.get("spawn_biome", "")
    spawn_zone = players_cfg.get("spawn_zone", "")

    # Find the spawn zone tiles
    spawn_positions = []
    if spawn_biome and spawn_zone:
        biome_file = biome_files.get(spawn_biome)
        if biome_file:
            biome_data = load_yaml(base_dir / biome_file)
            biome_offset = biome_data.get("biome", {}).get("grid_offset", [0, 0])
            for zone in biome_data.get("zones", []):
                if zone.get("id") == spawn_zone:
                    for t in zone.get("tiles", []):
                        spawn_positions.append(
                            (t[0] + biome_offset[0], t[1] + biome_offset[1]))
                    break

    for i, char in enumerate(players_cfg.get("characters", [])):
        entity_dict = build_entity_dict(char)
        entity_dict["entity_type"] = "player"
        # Place at spawn position
        if i < len(spawn_positions):
            pos = spawn_positions[i]
            if pos in tiles:
                tiles[pos]["entities"].append(entity_dict)
                tiles[pos]["tags"] = list(set(tiles[pos].get("tags", []) + ["START_ZONE"]))

    # Build final map.json
    map_data = {
        "version": "1.0",
        "meta": {
            "map_name": world_cfg.get("name", "Untitled World"),
            "author": world_cfg.get("author", "DnD World Builder"),
            "created": datetime.now().isoformat(),
            "grid_type": "square",
            "rows": total_rows,
            "cols": total_cols,
        },
        "tiles": [tiles[(r, c)] for r in range(total_rows) for c in range(total_cols)],
        "quests": all_quests,
    }

    return map_data


def main():
    parser = argparse.ArgumentParser(description="Compile biome YAMLs into map.json")
    parser.add_argument("input", type=Path, help="World YAML file")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output directory (default: workspace/<world_id>)")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: {args.input} not found")
        sys.exit(1)

    print(f"Compiling: {args.input}")
    map_data = compile_world(args.input)

    # Determine output dir
    if args.output:
        out_dir = args.output
    else:
        world = load_yaml(args.input)
        world_id = world.get("world", {}).get("id", "compiled")
        out_dir = Path("workspace") / world_id

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "map.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(map_data, f, indent=2, ensure_ascii=False)

    # Stats
    total_tiles = len(map_data["tiles"])
    entity_count = sum(len(t.get("entities", [])) for t in map_data["tiles"])
    trigger_count = sum(len(t.get("triggers", [])) for t in map_data["tiles"])
    labeled_tiles = sum(1 for t in map_data["tiles"] if t.get("user_label"))

    print(f"\nWritten: {out_file}")
    print(f"  Grid: {map_data['meta']['rows']}x{map_data['meta']['cols']} ({total_tiles} tiles)")
    print(f"  Entities: {entity_count}")
    print(f"  Triggers: {trigger_count}")
    print(f"  Labeled tiles: {labeled_tiles}")


if __name__ == "__main__":
    main()

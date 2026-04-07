"""Built-in terrain presets for quick-build combat encounters."""

from __future__ import annotations

from typing import Dict, List, Optional

from models.combat.encounter_template import TerrainPreset

TERRAIN_PRESETS: Dict[str, TerrainPreset] = {}


def register_preset(preset: TerrainPreset) -> None:
    """Register a terrain preset."""
    TERRAIN_PRESETS[preset.preset_id] = preset


def get_preset(preset_id: str) -> Optional[TerrainPreset]:
    """Get a terrain preset by ID."""
    return TERRAIN_PRESETS.get(preset_id)


def list_presets() -> List[TerrainPreset]:
    """List all registered terrain presets."""
    return list(TERRAIN_PRESETS.values())


# ── Built-in presets ─────────────────────────────────────────────────────

register_preset(TerrainPreset(
    preset_id="forest",
    name="Forest",
    base_terrain="grass",
    obstacles=[
        {"terrain": "wall", "label": "Tree", "blocks_vision": True,
         "blocks_movement": True, "size": [1, 1], "weight": 1.0, "elevation": 2},
        {"terrain": "difficult", "label": "Underbrush", "blocks_vision": False,
         "blocks_movement": False, "size": [1, 1], "weight": 0.5, "elevation": 0},
    ],
    obstacle_density=0.12,
    difficult_terrain_chance=0.08,
))

register_preset(TerrainPreset(
    preset_id="tavern",
    name="Tavern Interior",
    base_terrain="floor",
    obstacles=[
        {"terrain": "wall", "label": "Table", "blocks_vision": False,
         "blocks_movement": True, "size": [2, 1], "weight": 1.0, "elevation": 1},
        {"terrain": "wall", "label": "Chair", "blocks_vision": False,
         "blocks_movement": True, "size": [1, 1], "weight": 0.7, "elevation": 0},
        {"terrain": "wall", "label": "Bar Counter", "blocks_vision": False,
         "blocks_movement": True, "size": [3, 1], "weight": 0.3, "elevation": 1},
    ],
    obstacle_density=0.15,
    difficult_terrain_chance=0.02,
))

register_preset(TerrainPreset(
    preset_id="dungeon",
    name="Dungeon Chamber",
    base_terrain="floor",
    obstacles=[
        {"terrain": "wall", "label": "Stone Pillar", "blocks_vision": True,
         "blocks_movement": True, "size": [1, 1], "weight": 1.0, "elevation": 2},
        {"terrain": "wall", "label": "Rubble", "blocks_vision": False,
         "blocks_movement": True, "size": [1, 1], "weight": 0.5, "elevation": 1},
    ],
    obstacle_density=0.08,
    difficult_terrain_chance=0.05,
))

register_preset(TerrainPreset(
    preset_id="cave",
    name="Natural Cave",
    base_terrain="floor",
    obstacles=[
        {"terrain": "wall", "label": "Stalagmite", "blocks_vision": True,
         "blocks_movement": True, "size": [1, 1], "weight": 1.0, "elevation": 2},
        {"terrain": "difficult", "label": "Uneven Ground", "blocks_vision": False,
         "blocks_movement": False, "size": [1, 1], "weight": 0.6, "elevation": 0},
        {"terrain": "wall", "label": "Boulder", "blocks_vision": True,
         "blocks_movement": True, "size": [2, 2], "weight": 0.2, "elevation": 2},
    ],
    obstacle_density=0.10,
    difficult_terrain_chance=0.10,
))

register_preset(TerrainPreset(
    preset_id="open_field",
    name="Open Field",
    base_terrain="grass",
    obstacles=[
        {"terrain": "wall", "label": "Rock", "blocks_vision": False,
         "blocks_movement": True, "size": [1, 1], "weight": 1.0, "elevation": 1},
    ],
    obstacle_density=0.03,
    difficult_terrain_chance=0.02,
))

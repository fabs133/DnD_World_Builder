"""Encounter template data models.

Defines the blueprint for combat encounters: grid layout, enemy spawn
markers, player spawn zones, and terrain presets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class EnemySpawn:
    """Marker for where an enemy should appear when combat starts.

    :param position: Grid coordinates (col, row).
    :param creature_index: SRD creature reference (e.g., ``"goblin"``).
    :param count: Number of creatures at this position.
    :param variance: Random +/- variance on count (0 = exact).
    """

    position: Tuple[int, int]
    creature_index: str
    count: int = 1
    variance: int = 0

    def to_dict(self) -> dict:
        return {
            "position": list(self.position),
            "creature_index": self.creature_index,
            "count": self.count,
            "variance": self.variance,
        }

    @classmethod
    def from_dict(cls, data: dict) -> EnemySpawn:
        return cls(
            position=tuple(data["position"]),
            creature_index=data["creature_index"],
            count=data.get("count", 1),
            variance=data.get("variance", 0),
        )


@dataclass
class TerrainPreset:
    """Defines auto-generated terrain for quick-build encounters.

    :param preset_id: Unique identifier (e.g., ``"forest"``).
    :param name: Display name.
    :param base_terrain: Default terrain type for empty grid cells.
    :param obstacles: List of obstacle definitions for auto-placement.
    :param obstacle_density: Fraction of grid cells that receive obstacles.
    :param difficult_terrain_chance: Per-cell probability of difficult terrain.
    """

    preset_id: str
    name: str
    base_terrain: str = "floor"
    obstacles: List[dict] = field(default_factory=list)
    obstacle_density: float = 0.1
    difficult_terrain_chance: float = 0.05

    def to_dict(self) -> dict:
        return {
            "preset_id": self.preset_id,
            "name": self.name,
            "base_terrain": self.base_terrain,
            "obstacles": self.obstacles,
            "obstacle_density": self.obstacle_density,
            "difficult_terrain_chance": self.difficult_terrain_chance,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TerrainPreset:
        return cls(
            preset_id=data["preset_id"],
            name=data["name"],
            base_terrain=data.get("base_terrain", "floor"),
            obstacles=data.get("obstacles", []),
            obstacle_density=data.get("obstacle_density", 0.1),
            difficult_terrain_chance=data.get("difficult_terrain_chance", 0.05),
        )


@dataclass
class EncounterTemplate:
    """A reusable combat encounter blueprint.

    :param template_id: Unique identifier.
    :param name: Display name.
    :param grid_width: Number of columns.
    :param grid_height: Number of rows.
    :param grid_type: ``"square"`` or ``"hex"``.
    :param enemy_spawns: List of enemy placement markers.
    :param player_spawn_zone: List of grid positions where players can start.
    :param environment_tags: Tags for the encounter environment.
    :param terrain_preset_id: Optional terrain preset for auto-generation.
    :param difficulty_label: Suggested difficulty.
    """

    template_id: str
    name: str
    grid_width: int = 10
    grid_height: int = 10
    grid_type: str = "square"
    enemy_spawns: List[EnemySpawn] = field(default_factory=list)
    player_spawn_zone: List[Tuple[int, int]] = field(default_factory=list)
    environment_tags: List[str] = field(default_factory=list)
    terrain_preset_id: Optional[str] = None
    difficulty_label: str = "medium"

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "grid_width": self.grid_width,
            "grid_height": self.grid_height,
            "grid_type": self.grid_type,
            "enemy_spawns": [s.to_dict() for s in self.enemy_spawns],
            "player_spawn_zone": [list(p) for p in self.player_spawn_zone],
            "environment_tags": self.environment_tags,
            "terrain_preset_id": self.terrain_preset_id,
            "difficulty_label": self.difficulty_label,
        }

    @classmethod
    def from_dict(cls, data: dict) -> EncounterTemplate:
        return cls(
            template_id=data["template_id"],
            name=data["name"],
            grid_width=data.get("grid_width", 10),
            grid_height=data.get("grid_height", 10),
            grid_type=data.get("grid_type", "square"),
            enemy_spawns=[EnemySpawn.from_dict(s) for s in data.get("enemy_spawns", [])],
            player_spawn_zone=[tuple(p) for p in data.get("player_spawn_zone", [])],
            environment_tags=data.get("environment_tags", []),
            terrain_preset_id=data.get("terrain_preset_id"),
            difficulty_label=data.get("difficulty_label", "medium"),
        )


@dataclass
class EncounterBinding:
    """Links an encounter template to a map location.

    :param template_id: Reference to an EncounterTemplate.
    :param location_type: ``"tile"`` or ``"zone"``.
    :param location_id: The tile_id or zone_id where this encounter is bound.
    :param trigger_mode: How combat starts: ``"manual"``, ``"on_enter"``, ``"trigger_event"``.
    :param trigger_id: If trigger_mode is ``"trigger_event"``, the trigger that fires this.
    :param once_only: If True, the encounter is consumed after use.
    """

    template_id: str
    location_type: str = "tile"
    location_id: str = ""
    trigger_mode: str = "manual"
    trigger_id: Optional[str] = None
    once_only: bool = True

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "location_type": self.location_type,
            "location_id": self.location_id,
            "trigger_mode": self.trigger_mode,
            "trigger_id": self.trigger_id,
            "once_only": self.once_only,
        }

    @classmethod
    def from_dict(cls, data: dict) -> EncounterBinding:
        return cls(
            template_id=data["template_id"],
            location_type=data.get("location_type", "tile"),
            location_id=data.get("location_id", ""),
            trigger_mode=data.get("trigger_mode", "manual"),
            trigger_id=data.get("trigger_id"),
            once_only=data.get("once_only", True),
        )

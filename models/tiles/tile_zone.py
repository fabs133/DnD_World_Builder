"""Spatial sub-division within a tile.

Zones represent distinct areas within a single map tile, such as rooms
in a building or areas in a clearing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class ZonePlacement:
    """An entity's placement within a zone for depth rendering.

    :param entity: The GameEntity being placed.
    :param depth: Depth layer (1=far, 2=mid, 3=near). Default 3.
    :param x_percent: Horizontal position 0.0-1.0. Default 0.5.
    :param interaction_radius: Pixel radius for interaction circle.
    :param interaction_types: Available interactions for this entity.
    """

    entity: Any
    depth: int = 3
    x_percent: float = 0.5
    interaction_radius: int = 40
    interaction_types: List[str] = field(default_factory=lambda: ["inspect"])

    def to_dict(self) -> dict:
        entity_data = self.entity.to_dict() if hasattr(self.entity, "to_dict") else self.entity
        return {
            "entity": entity_data,
            "depth": self.depth,
            "x_percent": self.x_percent,
            "interaction_radius": self.interaction_radius,
            "interaction_types": self.interaction_types,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ZonePlacement:
        from models.entities.game_entity import GameEntity
        entity_data = data.get("entity", data)
        entity = GameEntity.from_dict(entity_data) if isinstance(entity_data, dict) else entity_data
        return cls(
            entity=entity,
            depth=data.get("depth", 3),
            x_percent=data.get("x_percent", 0.5),
            interaction_radius=data.get("interaction_radius", 40),
            interaction_types=data.get("interaction_types", ["inspect"]),
        )


@dataclass
class TileZone:
    """A spatial sub-division within a tile.

    :param zone_id: Unique identifier within the parent tile.
    :param label: Human-readable display name.
    :param description: Optional flavor text shown to players on entry.
    :param background_image: Optional path to a background image.
    :param connections: Zone IDs this zone connects to.
    :param locked: Whether the zone requires a check or key to enter.
    :param lock_dc: Difficulty class for lockpicking/force if locked.
    :param tags: Freeform tags for trigger conditions.
    :param encounter_template_id: Optional encounter template bound to this zone.
    :param placements: Entity placements with depth and position data.
    """

    zone_id: str
    label: str
    description: Optional[str] = None
    background_image: Optional[str] = None
    connections: List[str] = field(default_factory=list)
    locked: bool = False
    lock_dc: int = 15
    tags: List[str] = field(default_factory=list)
    encounter_template_id: Optional[str] = None
    placements: List[ZonePlacement] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = {
            "zone_id": self.zone_id,
            "label": self.label,
            "description": self.description,
            "background_image": self.background_image,
            "connections": self.connections,
            "locked": self.locked,
            "lock_dc": self.lock_dc,
            "tags": self.tags,
            "encounter_template_id": self.encounter_template_id,
        }
        if self.placements:
            data["placements"] = [p.to_dict() for p in self.placements]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> TileZone:
        placements = [ZonePlacement.from_dict(p) for p in data.get("placements", [])]
        return cls(
            zone_id=data["zone_id"],
            label=data["label"],
            description=data.get("description"),
            background_image=data.get("background_image"),
            connections=data.get("connections", []),
            locked=data.get("locked", False),
            lock_dc=data.get("lock_dc", 15),
            tags=data.get("tags", []),
            encounter_template_id=data.get("encounter_template_id"),
            placements=placements,
        )

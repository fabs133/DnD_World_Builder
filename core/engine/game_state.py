"""Immutable snapshot of the game state for observation and AI consumption."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EntitySnapshot:
    """Read-only view of an entity at a point in time."""

    name: str
    entity_type: str
    hp: int
    max_hp: int
    armor_class: int
    position: tuple[int, int]
    conditions: tuple[str, ...]
    stats: dict[str, Any]
    speed: int
    initiative_roll: int = 0
    faction: str = "neutral"
    is_alive: bool = True


@dataclass(frozen=True)
class TileSnapshot:
    """Read-only view of a tile."""

    position: tuple[int, int]
    terrain: str
    tags: tuple[str, ...]
    entity_names: tuple[str, ...]


@dataclass(frozen=True)
class GameState:
    """Immutable snapshot of the entire game at a point in time."""

    round_number: int
    current_entity_name: str
    entities: tuple[EntitySnapshot, ...]
    initiative_order: tuple[str, ...]
    world_width: int
    world_height: int
    tile_type: str
    tiles: tuple[TileSnapshot, ...] = ()
    event_log: tuple[str, ...] = ()
    seed: int = 0

    def get_entity(self, name: str) -> EntitySnapshot | None:
        """Look up entity by name."""
        for e in self.entities:
            if e.name == name:
                return e
        return None

    def get_enemies_of(self, entity_name: str) -> tuple[EntitySnapshot, ...]:
        """Get all living entities hostile to the named entity."""
        entity = self.get_entity(entity_name)
        if entity is None:
            return ()
        return tuple(
            e for e in self.entities
            if e.is_alive and e.faction != entity.faction and e.name != entity_name
        )

    def get_allies_of(self, entity_name: str) -> tuple[EntitySnapshot, ...]:
        """Get all living entities allied with the named entity."""
        entity = self.get_entity(entity_name)
        if entity is None:
            return ()
        return tuple(
            e for e in self.entities
            if e.is_alive and e.faction == entity.faction and e.name != entity_name
        )

    def get_entities_at(self, x: int, y: int) -> tuple[EntitySnapshot, ...]:
        """Get entities at a tile position."""
        return tuple(e for e in self.entities if e.position == (x, y))

    @classmethod
    def from_gamemaster(
        cls,
        gm,
        round_number: int,
        current_entity_name: str,
        initiative_order: list[str],
        seed: int = 0,
        event_log: list[str] | None = None,
    ) -> GameState:
        """Create snapshot from mutable Gamemaster state."""
        entity_snapshots = []
        for entity in gm.game_entities:
            pos = getattr(entity, "position", (0, 0))
            hp = getattr(entity, "hp", 0)
            max_hp = getattr(entity, "stats", {}).get("max_hp", hp)
            ac = getattr(entity, "armor_class", 10)
            conditions = tuple(getattr(entity, "conditions", []))
            speed = getattr(entity, "speed", 30)
            initiative_roll = getattr(entity, "initiative", 0)
            faction = _infer_faction(entity)

            entity_snapshots.append(EntitySnapshot(
                name=entity.name,
                entity_type=entity.entity_type,
                hp=hp,
                max_hp=max_hp,
                armor_class=ac,
                position=pos,
                conditions=conditions,
                stats=dict(getattr(entity, "stats", {})),
                speed=speed,
                initiative_roll=initiative_roll,
                faction=faction,
                is_alive=hp > 0,
            ))

        tile_snapshots = []
        for pos, tile in gm.world_tile_manager.tiles.items():
            entities_at = gm.world_tile_manager.get_entities_at(pos[0], pos[1])
            tile_snapshots.append(TileSnapshot(
                position=pos,
                terrain=tile.terrain.value if hasattr(tile.terrain, "value") else str(tile.terrain),
                tags=tuple(t.value if hasattr(t, "value") else str(t) for t in tile.tags),
                entity_names=tuple(e.name for e in entities_at),
            ))

        return cls(
            round_number=round_number,
            current_entity_name=current_entity_name,
            entities=tuple(entity_snapshots),
            initiative_order=tuple(initiative_order),
            world_width=gm.world_tile_manager.width,
            world_height=gm.world_tile_manager.height,
            tile_type=gm.world_tile_manager.tile_type,
            tiles=tuple(tile_snapshots),
            event_log=tuple(event_log or []),
            seed=seed,
        )


def _infer_faction(entity) -> str:
    """Infer faction from entity_type if no explicit faction attribute."""
    if hasattr(entity, "faction"):
        return entity.faction
    etype = getattr(entity, "entity_type", "").lower()
    if etype in ("player", "ally"):
        return "player"
    if etype in ("enemy",):
        return "enemy"
    return "neutral"

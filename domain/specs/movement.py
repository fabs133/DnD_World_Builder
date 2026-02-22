"""
D&D 5e Movement and Terrain Specifications

This module implements movement rules as composable specifications:
- Movement resource checks
- Terrain passability
- Spatial constraints (range, adjacency)
- Movement-blocking conditions

These specs are designed to work with:
- EntityState (or any object with position, movement_remaining)
- TileState (or any object with terrain, entities)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from enum import Enum

from domain.specs.base import Specification, SpecResult, AnyOf


class TerrainType(Enum):
    """Standard D&D terrain types."""
    NORMAL = "normal"
    DIFFICULT = "difficult"
    WATER = "water"
    DEEP_WATER = "deep_water"
    WALL = "wall"
    PIT = "pit"
    LAVA = "lava"
    ICE = "ice"
    MUD = "mud"


@dataclass
class MovementMode:
    """An entity's movement capabilities."""
    walk: int = 30
    swim: int = 0
    fly: int = 0
    climb: int = 0
    burrow: int = 0
    
    def can_traverse(self, terrain: TerrainType) -> bool:
        """Check if this movement mode can traverse terrain type."""
        if terrain == TerrainType.WALL:
            return self.burrow > 0  # Only burrowing creatures pass walls
        if terrain in (TerrainType.WATER, TerrainType.DEEP_WATER):
            return self.swim > 0 or self.fly > 0
        if terrain == TerrainType.PIT:
            return self.fly > 0
        return True


class HasMovementRemaining(Specification):
    """
    Check if entity has enough movement remaining this turn.
    
    Args:
        required: Feet of movement required (default 5 for one square)
        
    Candidate requirements:
        - movement_remaining: int (feet of movement left this turn)
    """
    
    def __init__(self, required: int = 5):
        self.required = required
    
    @property
    def rule_id(self) -> str:
        return f"has_movement_{self.required}"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        available = self._get_movement(candidate)
        passed = available >= self.required
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=passed,
            message=f"Movement: need {self.required}ft, have {available}ft",
            suggested_fix=None if passed else "Use Dash action for extra movement",
            tags=frozenset({"movement", "resource"}),
            data={
                "required": self.required,
                "available": available,
                "deficit": max(0, self.required - available),
            }
        )
    
    def _get_movement(self, candidate: Any) -> int:
        if hasattr(candidate, "movement_remaining"):
            return candidate.movement_remaining
        if isinstance(candidate, dict):
            return candidate.get("movement_remaining", 0)
        return 0
    
    def to_dict(self) -> dict[str, Any]:
        return {"type": "HasMovementRemaining", "required": self.required}
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HasMovementRemaining:
        return cls(required=data.get("required", 5))


class TileIsPassable(Specification):
    """
    Check if a tile's terrain allows passage.
    
    Args:
        allow_difficult: Whether difficult terrain is passable (default True)
        
    Candidate: The tile to check
    Context: May contain movement_mode for special movement
    """
    
    # Terrain that blocks all normal movement
    IMPASSABLE = {TerrainType.WALL, TerrainType.LAVA}
    
    # Terrain requiring special movement
    REQUIRES_SPECIAL = {
        TerrainType.WATER: "swim",
        TerrainType.DEEP_WATER: "swim",
        TerrainType.PIT: "fly",
    }
    
    def __init__(self, allow_difficult: bool = True):
        self.allow_difficult = allow_difficult
    
    @property
    def rule_id(self) -> str:
        return "tile_passable"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        context = context or {}
        terrain = self._get_terrain(candidate)
        movement_mode = context.get("movement_mode")
        
        # Check for absolutely impassable terrain
        if terrain in self.IMPASSABLE:
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message=f"Cannot pass through {terrain.value}",
                suggested_fix=self._get_fix_for_terrain(terrain),
                tags=frozenset({"movement", "terrain", terrain.value}),
                data={"terrain": terrain.value, "reason": "impassable"}
            )
        
        # Check terrain requiring special movement
        if terrain in self.REQUIRES_SPECIAL:
            required_mode = self.REQUIRES_SPECIAL[terrain]
            has_mode = self._has_movement_mode(movement_mode, required_mode)
            
            if not has_mode:
                return SpecResult(
                    rule_id=self.rule_id,
                    passed=False,
                    message=f"Cannot enter {terrain.value} without {required_mode} speed",
                    suggested_fix=f"Acquire {required_mode} movement or find another path",
                    tags=frozenset({"movement", "terrain", terrain.value}),
                    data={
                        "terrain": terrain.value,
                        "required_mode": required_mode,
                        "reason": "missing_movement_mode"
                    }
                )
        
        # Check difficult terrain
        if terrain == TerrainType.DIFFICULT and not self.allow_difficult:
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message="Difficult terrain not allowed for this movement",
                tags=frozenset({"movement", "terrain", "difficult"}),
                data={"terrain": terrain.value, "reason": "difficult_blocked"}
            )
        
        # Passable
        cost_multiplier = 2 if terrain == TerrainType.DIFFICULT else 1
        return SpecResult(
            rule_id=self.rule_id,
            passed=True,
            message=f"Terrain passable ({terrain.value})",
            tags=frozenset({"movement", "terrain"}),
            data={
                "terrain": terrain.value,
                "cost_multiplier": cost_multiplier,
            }
        )
    
    def _get_terrain(self, candidate: Any) -> TerrainType:
        if hasattr(candidate, "terrain"):
            t = candidate.terrain
            return t if isinstance(t, TerrainType) else TerrainType(t)
        if isinstance(candidate, dict):
            t = candidate.get("terrain", "normal")
            return TerrainType(t) if isinstance(t, str) else t
        return TerrainType.NORMAL
    
    def _has_movement_mode(self, movement_mode: Any, required: str) -> bool:
        if movement_mode is None:
            return False
        if isinstance(movement_mode, MovementMode):
            return getattr(movement_mode, required, 0) > 0
        if isinstance(movement_mode, dict):
            return movement_mode.get(required, 0) > 0
        return False
    
    def _get_fix_for_terrain(self, terrain: TerrainType) -> str:
        fixes = {
            TerrainType.WALL: "Use Passwall spell or find another route",
            TerrainType.LAVA: "Use Fly spell or find a way around",
            TerrainType.PIT: "Jump across, use Fly, or find a bridge",
        }
        return fixes.get(terrain, "Find another path")
    
    def to_dict(self) -> dict[str, Any]:
        return {"type": "TileIsPassable", "allow_difficult": self.allow_difficult}


class TileNotOccupied(Specification):
    """
    Check if a tile is not occupied by blocking entities.
    
    In D&D 5e:
    - Cannot end movement in another creature's space (usually)
    - Can move THROUGH allied creatures
    - Moving through enemy space costs extra movement
    
    Args:
        allow_allies: Can share space with allies (for passing through)
        check_ending_position: If True, applies full occupation rules
    """
    
    def __init__(self, allow_allies: bool = True, check_ending_position: bool = True):
        self.allow_allies = allow_allies
        self.check_ending_position = check_ending_position
    
    @property
    def rule_id(self) -> str:
        return "tile_not_occupied"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        context = context or {}
        mover_faction = context.get("mover_faction", "player")
        entities = self._get_entities(candidate)
        
        blockers = []
        for entity in entities:
            if not self._blocks_movement(entity):
                continue
            
            entity_faction = self._get_faction(entity)
            
            # Allies don't block if allow_allies
            if self.allow_allies and entity_faction == mover_faction:
                continue
            
            blockers.append(entity)
        
        if blockers:
            blocker_names = [self._get_name(e) for e in blockers]
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message=f"Tile occupied by: {', '.join(blocker_names)}",
                suggested_fix="Defeat, move around, or use special ability to pass",
                tags=frozenset({"movement", "occupation", "blocked"}),
                data={
                    "blockers": blocker_names,
                    "blocker_count": len(blockers),
                }
            )
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=True,
            message="Tile not occupied by blocking creatures",
            tags=frozenset({"movement", "occupation"}),
        )
    
    def _get_entities(self, candidate: Any) -> list:
        if hasattr(candidate, "entities"):
            return list(candidate.entities)
        if isinstance(candidate, dict):
            return candidate.get("entities", [])
        return []
    
    def _blocks_movement(self, entity: Any) -> bool:
        if hasattr(entity, "blocks_movement"):
            return entity.blocks_movement
        if hasattr(entity, "entity_type"):
            # Standard D&D: creatures block, objects might not
            return entity.entity_type in ("player", "npc", "enemy")
        return True
    
    def _get_faction(self, entity: Any) -> str:
        if hasattr(entity, "faction"):
            return entity.faction
        if hasattr(entity, "entity_type"):
            return entity.entity_type  # Treat type as faction fallback
        return "neutral"
    
    def _get_name(self, entity: Any) -> str:
        if hasattr(entity, "name"):
            return entity.name
        if isinstance(entity, dict):
            return entity.get("name", "Unknown")
        return "Unknown"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "TileNotOccupied",
            "allow_allies": self.allow_allies,
            "check_ending_position": self.check_ending_position,
        }


class InRange(Specification):
    """
    Check if a position is within range of another position.
    
    Supports multiple distance calculations for different grid types.
    
    Args:
        target: Target position (x, y) or object with .position
        max_range: Maximum range in feet
        min_range: Minimum range in feet (for reach weapons, etc.)
        grid_size: Feet per grid square (default 5)
    """
    
    def __init__(
        self,
        target: tuple[int, int] | Any,
        max_range: int,
        min_range: int = 0,
        grid_size: int = 5,
    ):
        self.target = target
        self.max_range = max_range
        self.min_range = min_range
        self.grid_size = grid_size
    
    @property
    def rule_id(self) -> str:
        return f"in_range_{self.min_range}_{self.max_range}"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        context = context or {}
        
        source_pos = self._get_position(candidate)
        target_pos = self._get_position(self.target)
        
        if source_pos is None or target_pos is None:
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message="Cannot determine positions for range check",
                tags=frozenset({"range", "error"}),
                data={"error": "missing_position"}
            )
        
        # Calculate distance (grid-based)
        distance = self._calculate_distance(source_pos, target_pos, context)
        
        in_max = distance <= self.max_range
        in_min = distance >= self.min_range
        passed = in_max and in_min
        
        if not in_max:
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message=f"Out of range: {distance}ft (max {self.max_range}ft)",
                suggested_fix=f"Move {distance - self.max_range}ft closer",
                tags=frozenset({"range", "too_far"}),
                data={
                    "distance": distance,
                    "max_range": self.max_range,
                    "overage": distance - self.max_range,
                }
            )
        
        if not in_min:
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message=f"Too close: {distance}ft (min {self.min_range}ft)",
                suggested_fix=f"Move {self.min_range - distance}ft away",
                tags=frozenset({"range", "too_close"}),
                data={
                    "distance": distance,
                    "min_range": self.min_range,
                    "underage": self.min_range - distance,
                }
            )
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=True,
            message=f"In range: {distance}ft",
            tags=frozenset({"range"}),
            data={
                "distance": distance,
                "max_range": self.max_range,
                "min_range": self.min_range,
            }
        )
    
    def _get_position(self, obj: Any) -> tuple[int, int] | None:
        if isinstance(obj, tuple) and len(obj) == 2:
            return obj
        if hasattr(obj, "position"):
            return obj.position
        if isinstance(obj, dict) and "position" in obj:
            return tuple(obj["position"])
        return None
    
    def _calculate_distance(
        self,
        a: tuple[int, int],
        b: tuple[int, int],
        context: dict[str, Any]
    ) -> int:
        """
        Calculate grid distance in feet.
        
        Uses Chebyshev distance (diagonals = 1 square) by default,
        which is common in D&D 5e.
        """
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        
        distance_mode = context.get("distance_mode", "chebyshev")
        
        if distance_mode == "manhattan":
            # No diagonal movement
            squares = dx + dy
        elif distance_mode == "chebyshev":
            # Diagonals = 1 square (D&D default)
            squares = max(dx, dy)
        elif distance_mode == "alternating":
            # 5e optional: diagonals alternate 5/10/5/10
            straight = abs(dx - dy)
            diagonals = min(dx, dy)
            squares = straight + diagonals + (diagonals // 2)
        else:
            squares = max(dx, dy)
        
        return squares * self.grid_size
    
    def to_dict(self) -> dict[str, Any]:
        target = self.target if isinstance(self.target, tuple) else None
        return {
            "type": "InRange",
            "target": target,
            "max_range": self.max_range,
            "min_range": self.min_range,
            "grid_size": self.grid_size,
        }


class IsAdjacent(InRange):
    """
    Check if positions are adjacent (within 5 feet).
    
    Convenience wrapper around InRange for melee range.
    """
    
    def __init__(self, target: tuple[int, int] | Any, grid_size: int = 5):
        super().__init__(target=target, max_range=grid_size, min_range=0, grid_size=grid_size)
    
    @property
    def rule_id(self) -> str:
        return "is_adjacent"


# ─────────────────────────────────────────────────────────────────────────────
# Composed Movement Specifications
# ─────────────────────────────────────────────────────────────────────────────

def can_move_to(
    distance: int = 5,
    allow_difficult: bool = True,
    allow_allies: bool = True,
) -> Specification:
    """
    Factory for the standard "can move to tile" check.
    
    Composes:
    - HasMovementRemaining
    - TileIsPassable
    - TileNotOccupied
    
    Usage:
        spec = can_move_to(distance=10)
        result = spec.is_satisfied_by(target_tile, context={
            "mover": entity,
            "mover_faction": "player"
        })
    
    Note: This evaluates the TILE. To check the ENTITY's movement,
    evaluate HasMovementRemaining against the entity separately.
    """
    return (
        TileIsPassable(allow_difficult=allow_difficult) &
        TileNotOccupied(allow_allies=allow_allies)
    )


class CanReachTile(Specification):
    """
    Full movement check: entity has movement AND tile is passable.
    
    This spec evaluates BOTH the entity (for movement remaining)
    and the tile (for passability) in a single check.
    
    Args:
        distance: Movement cost in feet
        tile: The target tile to check
    """
    
    def __init__(self, distance: int, tile: Any):
        self.distance = distance
        self.tile = tile
        self._movement_spec = HasMovementRemaining(distance)
        self._tile_spec = can_move_to(distance)
    
    @property
    def rule_id(self) -> str:
        return f"can_reach_tile_{self.distance}ft"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        """
        Args:
            candidate: The entity attempting to move
            context: Should include 'mover_faction' for occupation checks
        """
        context = context or {}
        
        # Check entity has movement
        movement_result = self._movement_spec.is_satisfied_by(candidate, context)
        if not movement_result.passed:
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message=movement_result.message,
                suggested_fix=movement_result.suggested_fix,
                tags=movement_result.tags | frozenset({"reach_check"}),
                data={"phase": "movement_check", "inner": movement_result.to_dict()}
            )
        
        # Check tile is passable
        tile_result = self._tile_spec.is_satisfied_by(self.tile, context)
        if not tile_result.passed:
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message=tile_result.message,
                suggested_fix=tile_result.suggested_fix,
                tags=tile_result.tags | frozenset({"reach_check"}),
                data={"phase": "tile_check", "inner": tile_result.to_dict()}
            )
        
        # Both passed
        return SpecResult(
            rule_id=self.rule_id,
            passed=True,
            message=f"Can reach tile ({self.distance}ft movement)",
            tags=frozenset({"movement", "reach_check"}),
            data={
                "distance": self.distance,
                "movement": movement_result.to_dict(),
                "tile": tile_result.to_dict(),
            }
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "CanReachTile",
            "distance": self.distance,
        }

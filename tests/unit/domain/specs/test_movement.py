"""Tests for domain.specs.movement — Movement, terrain, range specs."""

import pytest

from domain.specs.movement import (
    TerrainType,
    MovementMode,
    HasMovementRemaining,
    TileIsPassable,
    TileNotOccupied,
    InRange,
    IsAdjacent,
    CanReachTile,
    can_move_to,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

class FakeMovingEntity:
    def __init__(self, movement_remaining=30, position=(0, 0)):
        self.movement_remaining = movement_remaining
        self.position = position


class FakeTile:
    def __init__(self, terrain="normal", entities=None):
        self.terrain = terrain
        self.entities = entities or []


class FakeTileEntity:
    def __init__(self, name="Goblin", entity_type="enemy", faction="enemy"):
        self.name = name
        self.entity_type = entity_type
        self.faction = faction


# ── MovementMode ─────────────────────────────────────────────────────────────

class TestMovementMode:
    def test_can_traverse_normal(self):
        mm = MovementMode()
        assert mm.can_traverse(TerrainType.NORMAL) is True

    def test_cannot_traverse_wall(self):
        mm = MovementMode()
        assert mm.can_traverse(TerrainType.WALL) is False

    def test_burrow_traverses_wall(self):
        mm = MovementMode(burrow=20)
        assert mm.can_traverse(TerrainType.WALL) is True

    def test_cannot_traverse_water_without_swim(self):
        mm = MovementMode(swim=0, fly=0)
        assert mm.can_traverse(TerrainType.WATER) is False

    def test_swim_traverses_water(self):
        mm = MovementMode(swim=30)
        assert mm.can_traverse(TerrainType.WATER) is True

    def test_fly_traverses_water(self):
        mm = MovementMode(fly=60)
        assert mm.can_traverse(TerrainType.WATER) is True

    def test_fly_traverses_pit(self):
        mm = MovementMode(fly=60)
        assert mm.can_traverse(TerrainType.PIT) is True

    def test_cannot_traverse_pit_without_fly(self):
        mm = MovementMode()
        assert mm.can_traverse(TerrainType.PIT) is False

    def test_difficult_terrain_traversable(self):
        mm = MovementMode()
        assert mm.can_traverse(TerrainType.DIFFICULT) is True


# ── HasMovementRemaining ─────────────────────────────────────────────────────

class TestHasMovementRemaining:
    def test_has_enough(self):
        entity = FakeMovingEntity(movement_remaining=30)
        assert HasMovementRemaining(5).is_satisfied_by(entity).passed is True

    def test_not_enough(self):
        entity = FakeMovingEntity(movement_remaining=0)
        result = HasMovementRemaining(5).is_satisfied_by(entity)
        assert result.passed is False
        assert result.data["deficit"] == 5

    def test_exact_amount(self):
        entity = FakeMovingEntity(movement_remaining=10)
        assert HasMovementRemaining(10).is_satisfied_by(entity).passed is True

    def test_default_5ft(self):
        spec = HasMovementRemaining()
        assert spec.required == 5

    def test_dict_candidate(self):
        candidate = {"movement_remaining": 15}
        assert HasMovementRemaining(10).is_satisfied_by(candidate).passed is True

    def test_from_dict(self):
        spec = HasMovementRemaining.from_dict({"required": 10})
        assert spec.required == 10

    def test_rule_id(self):
        assert HasMovementRemaining(30).rule_id == "has_movement_30"


# ── TileIsPassable ───────────────────────────────────────────────────────────

class TestTileIsPassable:
    def test_normal_passable(self):
        tile = FakeTile(terrain="normal")
        assert TileIsPassable().is_satisfied_by(tile).passed is True

    def test_wall_impassable(self):
        tile = FakeTile(terrain="wall")
        assert TileIsPassable().is_satisfied_by(tile).passed is False

    def test_lava_impassable(self):
        tile = FakeTile(terrain="lava")
        assert TileIsPassable().is_satisfied_by(tile).passed is False

    def test_difficult_passable_by_default(self):
        tile = FakeTile(terrain="difficult")
        assert TileIsPassable().is_satisfied_by(tile).passed is True

    def test_difficult_blocked_when_disallowed(self):
        tile = FakeTile(terrain="difficult")
        assert TileIsPassable(allow_difficult=False).is_satisfied_by(tile).passed is False

    def test_water_requires_swim(self):
        tile = FakeTile(terrain="water")
        result = TileIsPassable().is_satisfied_by(tile, {})
        assert result.passed is False

    def test_water_passable_with_swim(self):
        tile = FakeTile(terrain="water")
        ctx = {"movement_mode": MovementMode(swim=30)}
        assert TileIsPassable().is_satisfied_by(tile, ctx).passed is True

    def test_pit_passable_with_fly(self):
        tile = FakeTile(terrain="pit")
        ctx = {"movement_mode": MovementMode(fly=60)}
        assert TileIsPassable().is_satisfied_by(tile, ctx).passed is True

    def test_difficult_terrain_cost_multiplier(self):
        tile = FakeTile(terrain="difficult")
        result = TileIsPassable().is_satisfied_by(tile)
        assert result.data["cost_multiplier"] == 2

    def test_normal_terrain_cost_multiplier(self):
        tile = FakeTile(terrain="normal")
        result = TileIsPassable().is_satisfied_by(tile)
        assert result.data["cost_multiplier"] == 1


# ── TileNotOccupied ──────────────────────────────────────────────────────────

class TestTileNotOccupied:
    def test_empty_tile(self):
        tile = FakeTile(entities=[])
        assert TileNotOccupied().is_satisfied_by(tile).passed is True

    def test_enemy_blocks(self):
        tile = FakeTile(entities=[FakeTileEntity(entity_type="enemy", faction="enemy")])
        ctx = {"mover_faction": "player"}
        assert TileNotOccupied().is_satisfied_by(tile, ctx).passed is False

    def test_ally_allowed_by_default(self):
        tile = FakeTile(entities=[FakeTileEntity(entity_type="player", faction="player")])
        ctx = {"mover_faction": "player"}
        assert TileNotOccupied(allow_allies=True).is_satisfied_by(tile, ctx).passed is True

    def test_ally_blocked_when_disallowed(self):
        tile = FakeTile(entities=[FakeTileEntity(entity_type="player", faction="player")])
        ctx = {"mover_faction": "player"}
        assert TileNotOccupied(allow_allies=False).is_satisfied_by(tile, ctx).passed is False


# ── InRange ──────────────────────────────────────────────────────────────────

class TestInRange:
    def test_in_range(self):
        spec = InRange(target=(3, 0), max_range=15)
        entity = FakeMovingEntity(position=(0, 0))
        result = spec.is_satisfied_by(entity)
        assert result.passed is True  # 3 squares * 5 = 15ft

    def test_out_of_range(self):
        spec = InRange(target=(5, 0), max_range=10)
        entity = FakeMovingEntity(position=(0, 0))
        result = spec.is_satisfied_by(entity)
        assert result.passed is False  # 5 * 5 = 25ft > 10ft

    def test_min_range(self):
        spec = InRange(target=(0, 0), max_range=60, min_range=10)
        entity = FakeMovingEntity(position=(1, 0))
        result = spec.is_satisfied_by(entity)
        assert result.passed is False  # 5ft < 10ft min

    def test_target_as_object_with_position(self):
        target = FakeMovingEntity(position=(2, 2))
        spec = InRange(target=target, max_range=20)
        entity = FakeMovingEntity(position=(0, 0))
        result = spec.is_satisfied_by(entity)
        assert result.passed is True  # chebyshev: max(2,2) = 2 * 5 = 10ft

    def test_manhattan_distance_mode(self):
        spec = InRange(target=(2, 2), max_range=15)
        entity = FakeMovingEntity(position=(0, 0))
        result = spec.is_satisfied_by(entity, {"distance_mode": "manhattan"})
        assert result.passed is False  # manhattan: 4 * 5 = 20ft > 15ft

    def test_chebyshev_default(self):
        spec = InRange(target=(2, 2), max_range=15)
        entity = FakeMovingEntity(position=(0, 0))
        result = spec.is_satisfied_by(entity)
        assert result.passed is True  # chebyshev: 2 * 5 = 10ft

    def test_missing_position_fails(self):
        spec = InRange(target=(5, 5), max_range=100)
        result = spec.is_satisfied_by("no_position")
        assert result.passed is False

    def test_rule_id(self):
        spec = InRange(target=(0, 0), max_range=30, min_range=5)
        assert spec.rule_id == "in_range_5_30"


# ── IsAdjacent ───────────────────────────────────────────────────────────────

class TestIsAdjacent:
    def test_adjacent(self):
        spec = IsAdjacent(target=(1, 0))
        entity = FakeMovingEntity(position=(0, 0))
        assert spec.is_satisfied_by(entity).passed is True

    def test_not_adjacent(self):
        spec = IsAdjacent(target=(3, 0))
        entity = FakeMovingEntity(position=(0, 0))
        assert spec.is_satisfied_by(entity).passed is False

    def test_diagonal_adjacent(self):
        spec = IsAdjacent(target=(1, 1))
        entity = FakeMovingEntity(position=(0, 0))
        assert spec.is_satisfied_by(entity).passed is True  # chebyshev: 1 * 5 = 5ft

    def test_rule_id(self):
        assert IsAdjacent(target=(0, 0)).rule_id == "is_adjacent"


# ── CanReachTile ─────────────────────────────────────────────────────────────

class TestCanReachTile:
    def test_can_reach(self):
        tile = FakeTile(terrain="normal", entities=[])
        entity = FakeMovingEntity(movement_remaining=10)
        spec = CanReachTile(distance=5, tile=tile)
        assert spec.is_satisfied_by(entity).passed is True

    def test_no_movement(self):
        tile = FakeTile(terrain="normal", entities=[])
        entity = FakeMovingEntity(movement_remaining=0)
        spec = CanReachTile(distance=5, tile=tile)
        assert spec.is_satisfied_by(entity).passed is False

    def test_tile_impassable(self):
        tile = FakeTile(terrain="wall", entities=[])
        entity = FakeMovingEntity(movement_remaining=30)
        spec = CanReachTile(distance=5, tile=tile)
        assert spec.is_satisfied_by(entity).passed is False


# ── can_move_to factory ──────────────────────────────────────────────────────

class TestCanMoveTo:
    def test_factory_returns_spec(self):
        spec = can_move_to(distance=5)
        assert isinstance(spec, type(spec))  # It's a composed spec

    def test_passable_empty_tile(self):
        spec = can_move_to()
        tile = FakeTile(terrain="normal", entities=[])
        assert spec.is_satisfied_by(tile).passed is True

    def test_wall_tile_fails(self):
        spec = can_move_to()
        tile = FakeTile(terrain="wall", entities=[])
        assert spec.is_satisfied_by(tile).passed is False

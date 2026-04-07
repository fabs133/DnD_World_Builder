"""Tests for elevation-aware pathfinder."""

import pytest
from models.world.world_tile_manager import WorldTileManager
from models.tiles.tile_data import TileData, TerrainType
from core.engine.pathfinder import reachable_tiles_with_elevation


def _make_grid(width=5, height=5):
    return WorldTileManager(width, height, tile_type="square")


class TestReachableWithElevation:

    def test_flat_grid_normal_cost(self):
        tm = _make_grid()
        combat_grid = {(x, y): tm.tiles[(x, y)] for x, y in tm.tiles}
        result = reachable_tiles_with_elevation((2, 2), 15, tm, combat_grid)
        assert (2, 2) in result
        assert result[(2, 2)]["cost"] == 0

    def test_step_up_normal_cost(self):
        tm = _make_grid()
        combat_grid = {(x, y): tm.tiles[(x, y)] for x, y in tm.tiles}
        combat_grid[(2, 1)].elevation = 1  # step up
        result = reachable_tiles_with_elevation((2, 2), 15, tm, combat_grid)
        assert (2, 1) in result
        assert result[(2, 1)]["traversal_type"] == "step"

    def test_climb_double_cost(self):
        tm = _make_grid()
        combat_grid = {(x, y): tm.tiles[(x, y)] for x, y in tm.tiles}
        combat_grid[(2, 1)].elevation = 2  # climb
        result = reachable_tiles_with_elevation((2, 2), 15, tm, combat_grid)
        assert (2, 1) in result
        assert result[(2, 1)]["cost"] == 10  # 5 * 2.0 multiplier
        assert result[(2, 1)]["traversal_type"] == "climb"

    def test_impassable_excluded(self):
        tm = _make_grid()
        combat_grid = {(x, y): tm.tiles[(x, y)] for x, y in tm.tiles}
        combat_grid[(2, 1)].elevation = 4  # impassable
        result = reachable_tiles_with_elevation((2, 2), 30, tm, combat_grid)
        assert (2, 1) not in result

    def test_no_combat_grid_normal(self):
        """Without combat grid, behaves like normal reachable_tiles."""
        tm = _make_grid()
        result = reachable_tiles_with_elevation((2, 2), 15, tm, None)
        assert (2, 2) in result
        assert result[(2, 2)]["traversal_type"] == "flat"

    def test_jump_down_reachable(self):
        tm = _make_grid()
        combat_grid = {(x, y): tm.tiles[(x, y)] for x, y in tm.tiles}
        combat_grid[(2, 2)].elevation = 3  # start high
        combat_grid[(2, 1)].elevation = 0  # jump down
        result = reachable_tiles_with_elevation((2, 2), 15, tm, combat_grid)
        assert (2, 1) in result
        assert result[(2, 1)]["traversal_type"] == "jump_down"


class TestElevationTraversableSpec:

    def test_flat_passes(self):
        from domain.specs.movement import ElevationTraversable
        spec = ElevationTraversable()
        result = spec.is_satisfied_by({"from_elevation": 0, "to_elevation": 0})
        assert result.passed
        assert result.data["traversal_type"] == "flat"

    def test_climb_passes_with_cost(self):
        from domain.specs.movement import ElevationTraversable
        spec = ElevationTraversable()
        result = spec.is_satisfied_by({"from_elevation": 0, "to_elevation": 2})
        assert result.passed
        assert result.data["cost_multiplier"] == 2.0

    def test_impassable_fails(self):
        from domain.specs.movement import ElevationTraversable
        spec = ElevationTraversable()
        result = spec.is_satisfied_by({"from_elevation": 0, "to_elevation": 4})
        assert not result.passed

    def test_flying_passes(self):
        from domain.specs.movement import ElevationTraversable
        spec = ElevationTraversable()
        result = spec.is_satisfied_by(
            {"from_elevation": 0, "to_elevation": 5},
            context={"has_fly_speed": True},
        )
        assert result.passed

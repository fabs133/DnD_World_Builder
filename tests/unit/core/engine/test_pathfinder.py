"""Tests for A* pathfinding and reachability."""

import pytest

from models.world.world_tile_manager import WorldTileManager
from models.tiles.tile_data import TileTag, TerrainType
from core.engine.pathfinder import find_path, reachable_tiles, path_cost


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_grid(width=5, height=5, tile_type="square"):
    """Create a blank square/hex grid."""
    return WorldTileManager(width, height, tile_type)


def _block_tile(tm, x, y):
    """Mark a tile as blocking."""
    tm.set_terrain_config(x, y, blocking=True)


def _set_cost(tm, x, y, cost):
    """Set custom movement cost (in feet) on a tile."""
    tm.set_terrain_config(x, y, movement_cost=cost)


# ── find_path tests ──────────────────────────────────────────────────────


class TestFindPath:
    def test_straight_path(self):
        tm = _make_grid(5, 5)
        path = find_path((0, 0), (4, 0), tm)
        assert path is not None
        assert path[0] == (0, 0)
        assert path[-1] == (4, 0)
        assert len(path) == 5  # (0,0) → (1,0) → (2,0) → (3,0) → (4,0)

    def test_path_around_wall(self):
        """A wall column blocks the direct route; path must go around."""
        tm = _make_grid(5, 5)
        # Wall column at x=2
        for y in range(5):
            _block_tile(tm, 2, y)
        # Unblock one gap
        tm.tiles[(2, 4)].tags.remove(TileTag.BLOCKS_MOVEMENT)

        path = find_path((0, 0), (4, 0), tm)
        assert path is not None
        assert path[0] == (0, 0)
        assert path[-1] == (4, 0)
        # Path must not pass through x=2 (except y=4 gap)
        for p in path:
            if p[0] == 2:
                assert p[1] == 4

    def test_blocking_goal_returns_none(self):
        tm = _make_grid(5, 5)
        _block_tile(tm, 4, 4)
        assert find_path((0, 0), (4, 4), tm) is None

    def test_completely_blocked_returns_none(self):
        """No path when surrounded by walls."""
        tm = _make_grid(3, 3)
        # Block all neighbors of (0, 0)
        _block_tile(tm, 1, 0)
        _block_tile(tm, 0, 1)
        assert find_path((0, 0), (2, 2), tm) is None

    def test_same_start_and_goal(self):
        tm = _make_grid(3, 3)
        path = find_path((1, 1), (1, 1), tm)
        assert path == [(1, 1)]

    def test_wall_terrain_is_blocking(self):
        tm = _make_grid(3, 3)
        tm.tiles[(1, 0)].terrain = TerrainType.WALL
        assert tm.is_blocking(1, 0)
        # Path must go around
        path = find_path((0, 0), (2, 0), tm)
        assert path is not None
        assert (1, 0) not in path

    def test_difficult_terrain_increases_cost(self):
        tm = _make_grid(5, 1)
        # Direct path: (0,0) → (1,0) → (2,0) → (3,0) → (4,0) costs 4*5=20
        # Make middle tile expensive
        _set_cost(tm, 2, 0, 10)  # 10ft instead of 5ft

        path = find_path((0, 0), (4, 0), tm)
        assert path is not None
        cost = path_cost(path, tm)
        assert cost == 25  # 5 + 10 + 5 + 5


class TestFindPathHex:
    def test_hex_path_basic(self):
        tm = _make_grid(5, 5, tile_type="hex")
        path = find_path((0, 0), (4, 0), tm)
        assert path is not None
        assert path[0] == (0, 0)
        assert path[-1] == (4, 0)

    def test_hex_path_around_wall(self):
        tm = _make_grid(5, 5, tile_type="hex")
        _block_tile(tm, 2, 0)
        _block_tile(tm, 2, 1)
        path = find_path((0, 0), (4, 0), tm)
        assert path is not None
        assert (2, 0) not in path
        assert (2, 1) not in path


# ── reachable_tiles tests ────────────────────────────────────────────────


class TestReachableTiles:
    def test_budget_limits_reach(self):
        tm = _make_grid(5, 5)
        reach = reachable_tiles((2, 2), budget=5, tile_map=tm)
        # Budget=5 means only adjacent tiles (cost 5 each) + origin
        assert (2, 2) in reach
        assert reach[(2, 2)] == 0
        # Adjacent tiles should cost 5
        for pos in [(1, 2), (3, 2), (2, 1), (2, 3)]:
            assert pos in reach
            assert reach[pos] == 5
        # Two tiles away should NOT be reachable
        assert (0, 2) not in reach

    def test_budget_10_reaches_two_steps(self):
        tm = _make_grid(5, 5)
        reach = reachable_tiles((2, 2), budget=10, tile_map=tm)
        assert (0, 2) in reach
        assert reach[(0, 2)] == 10

    def test_blocking_tiles_excluded(self):
        tm = _make_grid(5, 5)
        _block_tile(tm, 3, 2)
        reach = reachable_tiles((2, 2), budget=5, tile_map=tm)
        assert (3, 2) not in reach

    def test_expensive_tile_reduces_reach(self):
        tm = _make_grid(5, 1)
        _set_cost(tm, 1, 0, 10)  # Double cost
        reach = reachable_tiles((0, 0), budget=10, tile_map=tm)
        # (1,0) costs 10 so is reachable
        assert (1, 0) in reach
        assert reach[(1, 0)] == 10
        # (2,0) would cost 10 + 5 = 15 > budget
        assert (2, 0) not in reach

    def test_origin_always_included(self):
        tm = _make_grid(3, 3)
        reach = reachable_tiles((1, 1), budget=0, tile_map=tm)
        assert reach == {(1, 1): 0}


# ── path_cost tests ──────────────────────────────────────────────────────


class TestPathCost:
    def test_normal_terrain(self):
        tm = _make_grid(5, 1)
        cost = path_cost([(0, 0), (1, 0), (2, 0)], tm)
        assert cost == 10  # 5 + 5

    def test_mixed_terrain(self):
        tm = _make_grid(5, 1)
        _set_cost(tm, 1, 0, 10)
        cost = path_cost([(0, 0), (1, 0), (2, 0)], tm)
        assert cost == 15  # 10 + 5

    def test_single_tile_path(self):
        tm = _make_grid(3, 3)
        assert path_cost([(1, 1)], tm) == 0

    def test_empty_path(self):
        tm = _make_grid(3, 3)
        assert path_cost([], tm) == 0


# ── WorldTileManager helper tests ────────────────────────────────────────


class TestTileManagerHelpers:
    def test_get_movement_cost_default(self):
        tm = _make_grid(3, 3)
        assert tm.get_movement_cost(0, 0) == 5

    def test_get_movement_cost_custom(self):
        tm = _make_grid(3, 3)
        _set_cost(tm, 1, 1, 10)
        assert tm.get_movement_cost(1, 1) == 10

    def test_is_blocking_default(self):
        tm = _make_grid(3, 3)
        assert not tm.is_blocking(0, 0)

    def test_is_blocking_after_set(self):
        tm = _make_grid(3, 3)
        _block_tile(tm, 1, 1)
        assert tm.is_blocking(1, 1)

    def test_is_blocking_wall_terrain(self):
        tm = _make_grid(3, 3)
        tm.tiles[(1, 1)].terrain = TerrainType.WALL
        assert tm.is_blocking(1, 1)

    def test_is_blocking_out_of_bounds(self):
        tm = _make_grid(3, 3)
        assert tm.is_blocking(10, 10)  # out-of-bounds = blocking

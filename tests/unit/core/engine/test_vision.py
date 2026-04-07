"""Tests for vision computation (compute_visible_tiles)."""

import pytest

from models.world.world import World
from models.tiles.tile_data import TileTag
from core.engine.vision import compute_visible_tiles


def _make_world(width=5, height=5):
    return World(
        world_version=1, width=width, height=height, tile_type="square",
        description="test", map_data={},
        time_of_day="day", weather_conditions="clear",
    )


class TestComputeVisibleTiles:

    def test_empty_grid_full_visibility(self):
        """Open grid — all tiles within range are visible."""
        world = _make_world(5, 5)
        visible = compute_visible_tiles(world, [((2, 2), 10)])
        # All 25 tiles should be visible (range 10 covers entire 5x5 grid)
        assert len(visible) == 25

    def test_limited_range(self):
        """Range limits which tiles are visible."""
        world = _make_world(5, 5)
        visible = compute_visible_tiles(world, [((0, 0), 2)])
        # Only tiles within Manhattan distance 2 from (0,0)
        assert (0, 0) in visible
        assert (1, 0) in visible
        assert (0, 1) in visible
        assert (2, 0) in visible
        # (3, 0) is distance 3, should NOT be visible
        assert (3, 0) not in visible

    def test_wall_blocks_vision(self):
        """BLOCKS_VISION tile stops LOS."""
        world = _make_world(5, 5)
        # Place a wall at (1, 0)
        world.tile_manager.tiles[(1, 0)].tags.append(TileTag.BLOCKS_VISION)

        visible = compute_visible_tiles(world, [((0, 0), 10)])
        # (0,0) itself is visible
        assert (0, 0) in visible
        # Tiles behind the wall along x-axis should be blocked
        # (2,0) is behind (1,0) from observer at (0,0)
        assert (2, 0) not in visible

    def test_multiple_observers_union(self):
        """Visible tiles are the union of all observers' views."""
        world = _make_world(5, 5)
        visible = compute_visible_tiles(world, [
            ((0, 0), 1),  # sees only immediate neighbors
            ((4, 4), 1),  # sees only immediate neighbors
        ])
        assert (0, 0) in visible
        assert (4, 4) in visible
        # Center is out of range of both
        assert (2, 2) not in visible

    def test_zero_range_sees_only_self(self):
        """Range 0 sees only the entity's own tile."""
        world = _make_world(5, 5)
        visible = compute_visible_tiles(world, [((2, 2), 0)])
        assert visible == {(2, 2)}

    def test_no_observers_empty(self):
        """No observers means nothing is visible."""
        world = _make_world(5, 5)
        visible = compute_visible_tiles(world, [])
        assert len(visible) == 0

"""Tests for line of sight and fog of war."""

from types import SimpleNamespace

import pytest

from core.engine.vision import (
    DEFAULT_VISION_TILES,
    FogOfWar,
    Visibility,
    can_see,
    grid_distance,
    line_between,
    visible_positions,
    vision_range_tiles,
)
from models.tiles.tile_data import TileTag


def _grid(rows, cols, tile_type="square", walls=()):
    tiles = {
        (r, c): SimpleNamespace(tags={TileTag.BLOCKS_VISION} if (r, c) in walls else set())
        for r in range(rows)
        for c in range(cols)
    }
    return SimpleNamespace(tiles=tiles, tile_type=tile_type)


class TestGeometry:

    def test_square_distance_is_chebyshev(self):
        assert grid_distance((0, 0), (3, 2), "square") == 3
        assert grid_distance((2, 2), (2, 2), "square") == 0

    @pytest.mark.parametrize("a,b,expected", [
        ((0, 0), (0, 1), 1),   # odd column neighbour (shifted down)
        ((1, 0), (0, 1), 1),   # odd column is shifted down, so (0,1) touches (1,0)
        ((0, 0), (1, 1), 2),   # not adjacent: (1,1) sits half a tile below (1,0)
        ((0, 0), (0, 2), 2),
        ((0, 0), (3, 0), 3),
    ])
    def test_hex_distance_odd_q(self, a, b, expected):
        assert grid_distance(a, b, "hex") == expected

    def test_hex_neighbours_of_even_column_are_distance_one(self):
        center = (2, 2)
        neighbours = [(1, 2), (3, 2), (1, 1), (2, 1), (1, 3), (2, 3)]
        assert all(grid_distance(center, n, "hex") == 1 for n in neighbours)

    @pytest.mark.parametrize("tile_type", ["square", "hex"])
    def test_line_is_contiguous_and_ends_at_target(self, tile_type):
        start, end = (0, 0), (4, 5)
        line = line_between(start, end, tile_type)
        assert line[-1] == end
        assert len(line) == grid_distance(start, end, tile_type)
        previous = start
        for pos in line:
            assert grid_distance(previous, pos, tile_type) == 1
            previous = pos

    def test_line_to_self_is_empty(self):
        assert line_between((1, 1), (1, 1), "square") == []


class TestLineOfSight:

    def test_wall_blocks_tiles_behind_it_but_is_itself_visible(self):
        grid = _grid(1, 5, walls={(0, 2)})
        assert can_see((0, 0), (0, 1), grid, 10)
        assert can_see((0, 0), (0, 2), grid, 10)
        assert not can_see((0, 0), (0, 3), grid, 10)

    def test_range_limit(self):
        grid = _grid(1, 6)
        assert can_see((0, 0), (0, 3), grid, 3)
        assert not can_see((0, 0), (0, 4), grid, 3)

    def test_off_map_target_is_not_visible(self):
        assert not can_see((0, 0), (9, 9), _grid(2, 2), 20)

    def test_hex_wall_blocks(self):
        grid = _grid(5, 1, tile_type="hex", walls={(2, 0)})
        assert can_see((0, 0), (2, 0), grid, 10)
        assert not can_see((0, 0), (4, 0), grid, 10)

    def test_visible_positions_unions_viewers(self):
        grid = _grid(1, 7, walls={(0, 3)})
        seen = visible_positions([((0, 0), 10), ((0, 6), 1)], grid)
        assert seen == {(0, 0), (0, 1), (0, 2), (0, 3), (0, 5), (0, 6)}

    def test_vision_range_default_and_override(self):
        assert vision_range_tiles(SimpleNamespace()) == DEFAULT_VISION_TILES
        assert vision_range_tiles(SimpleNamespace(vision_range=None)) == DEFAULT_VISION_TILES
        assert vision_range_tiles(SimpleNamespace(vision_range=4)) == 4


class TestFogOfWar:

    def test_states_progress_hidden_visible_explored(self):
        fog = FogOfWar()
        assert fog.state((0, 0)) is Visibility.HIDDEN
        fog.update({(0, 0), (0, 1)})
        assert fog.state((0, 0)) is Visibility.VISIBLE
        fog.update({(0, 1)})
        assert fog.state((0, 0)) is Visibility.EXPLORED
        assert fog.state((5, 5)) is Visibility.HIDDEN

    def test_reset_forgets_everything(self):
        fog = FogOfWar()
        fog.update({(0, 0)})
        fog.reset()
        assert fog.state((0, 0)) is Visibility.HIDDEN

"""Tests for the distance measurement module."""

import pytest
from unittest.mock import MagicMock

from core.engine.measure import measure_distance, format_measurement, MeasureResult


@pytest.fixture
def tile_map():
    """5x5 square grid tile map mock with standard 5ft cost."""
    tm = MagicMock()
    tm.tile_type = "square"

    def get_adjacent(x, y):
        neighbours = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < 5 and 0 <= ny < 5:
                neighbours.append((nx, ny))
        return neighbours

    tm.get_adjacent_tiles.side_effect = get_adjacent
    tm.get_movement_cost.return_value = 5
    tm.is_blocking.return_value = False
    return tm


@pytest.fixture
def blocked_map(tile_map):
    """Tile map with a wall at (2, 2)."""
    original = tile_map.is_blocking.side_effect

    def is_blocking(x, y):
        return (x, y) == (2, 2)

    tile_map.is_blocking.side_effect = is_blocking
    return tile_map


class TestMeasureDistance:

    def test_same_tile(self, tile_map):
        result = measure_distance((0, 0), (0, 0), tile_map)
        assert result.cost_feet == 0
        assert result.tile_count == 1
        assert result.path == [(0, 0)]

    def test_adjacent_tile(self, tile_map):
        result = measure_distance((0, 0), (0, 1), tile_map)
        assert result.cost_feet == 5
        assert result.tile_count == 2
        assert result.path is not None
        assert result.path[0] == (0, 0)
        assert result.path[-1] == (0, 1)

    def test_multi_tile_path(self, tile_map):
        result = measure_distance((0, 0), (0, 4), tile_map)
        assert result.cost_feet == 20  # 4 tiles * 5ft
        assert result.tile_count == 5
        assert result.path[0] == (0, 0)
        assert result.path[-1] == (0, 4)

    def test_diagonal_path(self, tile_map):
        result = measure_distance((0, 0), (2, 2), tile_map)
        assert result.path is not None
        assert result.cost_feet > 0
        # Manhattan distance on 4-connected grid: need at least 4 steps
        assert result.tile_count >= 5

    def test_blocked_destination(self, blocked_map):
        result = measure_distance((0, 0), (2, 2), blocked_map)
        assert result.path is None
        assert result.cost_feet == -1
        assert result.tile_count == 0

    def test_path_around_wall(self, blocked_map):
        result = measure_distance((2, 1), (2, 3), blocked_map)
        assert result.path is not None
        assert (2, 2) not in result.path  # wall tile not in path

    def test_straight_line_tiles(self, tile_map):
        result = measure_distance((0, 0), (3, 0), tile_map)
        assert result.straight_line_tiles == 3

    def test_result_is_frozen_dataclass(self, tile_map):
        result = measure_distance((0, 0), (1, 0), tile_map)
        assert isinstance(result, MeasureResult)
        with pytest.raises(AttributeError):
            result.cost_feet = 999


class TestFormatMeasurement:

    def test_same_tile(self):
        result = MeasureResult(
            start=(0, 0), end=(0, 0),
            path=[(0, 0)], cost_feet=0,
            tile_count=1, straight_line_tiles=0,
        )
        assert "0ft" in format_measurement(result)

    def test_normal_path(self):
        result = MeasureResult(
            start=(0, 0), end=(0, 3),
            path=[(0, 0), (0, 1), (0, 2), (0, 3)],
            cost_feet=15, tile_count=4, straight_line_tiles=3,
        )
        text = format_measurement(result)
        assert "4 tiles" in text
        assert "15ft" in text
        assert "straight: 3" in text

    def test_no_path(self):
        result = MeasureResult(
            start=(0, 0), end=(4, 4),
            path=None, cost_feet=-1,
            tile_count=0, straight_line_tiles=4,
        )
        text = format_measurement(result)
        assert "No path" in text

"""Tests for tile hover and selection feedback."""

import pytest
from models.tiles.square_tile_item import SquareTileItem
from models.tiles.tile_data import TileData, TerrainType


@pytest.fixture
def tile(qapp):
    td = TileData(position=(2, 3), terrain=TerrainType.FLOOR)
    return SquareTileItem(0, 0, 50, tile_data=td)


class TestTileHover:

    def test_accepts_hover_events(self, tile):
        assert tile.acceptHoverEvents() is True

    def test_hover_flag_initially_false(self, tile):
        assert tile._hovered is False

    def test_set_hovered(self, tile):
        tile._hovered = True
        assert tile._hovered is True

    def test_clear_hovered(self, tile):
        tile._hovered = True
        tile._hovered = False
        assert tile._hovered is False


class TestTileSelection:

    def test_selected_initially_false(self, tile):
        assert tile._selected_highlight is False

    def test_set_selected_highlight_true(self, tile):
        tile.set_selected_highlight(True)
        assert tile._selected_highlight is True

    def test_set_selected_highlight_false(self, tile):
        tile.set_selected_highlight(True)
        tile.set_selected_highlight(False)
        assert tile._selected_highlight is False

    def test_single_selection(self, qapp):
        td1 = TileData(position=(0, 0), terrain=TerrainType.FLOOR)
        td2 = TileData(position=(1, 0), terrain=TerrainType.FLOOR)
        t1 = SquareTileItem(0, 0, 50, tile_data=td1)
        t2 = SquareTileItem(50, 0, 50, tile_data=td2)

        t1.set_selected_highlight(True)
        t2.set_selected_highlight(True)
        t1.set_selected_highlight(False)

        assert t1._selected_highlight is False
        assert t2._selected_highlight is True

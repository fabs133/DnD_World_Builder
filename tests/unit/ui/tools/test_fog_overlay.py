"""Tests for FogOverlay Qt rendering."""

import pytest

from PyQt5.QtWidgets import QGraphicsScene

from core.engine.fog_state import FogOfWarState
from ui.tools.fog_overlay import FogOverlay


@pytest.fixture
def scene():
    return QGraphicsScene()


@pytest.fixture
def overlay(scene):
    return FogOverlay(scene, tile_size=50)


class TestFogOverlay:

    def test_initially_empty(self, overlay):
        assert not overlay.is_visible

    def test_hidden_tiles_get_overlay(self, overlay):
        fog = FogOfWarState()  # all hidden
        overlay.update(fog, 3, 3)
        # 9 tiles, all hidden → 9 overlay rects
        assert overlay.is_visible
        assert len(overlay._items) == 9

    def test_visible_tiles_no_overlay(self, overlay):
        fog = FogOfWarState()
        fog.update({(x, y) for x in range(3) for y in range(3)})
        overlay.update(fog, 3, 3)
        # All visible → no overlay items
        assert len(overlay._items) == 0

    def test_revealed_tiles_get_semi_overlay(self, overlay):
        fog = FogOfWarState()
        fog.update({(0, 0), (1, 0)})
        fog.update({(0, 0)})  # (1,0) becomes revealed
        overlay.update(fog, 2, 2)
        # (0,0) visible → no overlay
        # (1,0) revealed → overlay
        # (0,1), (1,1) hidden → overlay
        assert len(overlay._items) == 3

    def test_clear_removes_all(self, overlay):
        fog = FogOfWarState()
        overlay.update(fog, 3, 3)
        assert overlay.is_visible
        overlay.clear()
        assert not overlay.is_visible
        assert len(overlay._items) == 0

    def test_update_replaces_previous(self, overlay):
        fog = FogOfWarState()
        overlay.update(fog, 2, 2)
        count1 = len(overlay._items)
        fog.update({(0, 0), (1, 0), (0, 1), (1, 1)})
        overlay.update(fog, 2, 2)
        # All visible now → 0 items
        assert len(overlay._items) == 0

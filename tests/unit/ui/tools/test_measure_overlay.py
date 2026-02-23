"""Tests for MeasureOverlay: drawing and clearing path highlights."""

import pytest

from PyQt5.QtWidgets import QGraphicsScene

from ui.tools.measure_overlay import MeasureOverlay


@pytest.fixture
def scene(qapp):
    return QGraphicsScene()


@pytest.fixture
def overlay(scene):
    return MeasureOverlay(scene, tile_size=50)


class TestMeasureOverlay:

    def test_initially_not_visible(self, overlay):
        assert not overlay.is_visible

    def test_show_path_adds_items(self, overlay, scene):
        path = [(0, 0), (0, 1), (0, 2)]
        overlay.show_path(path, cost_feet=10)
        assert overlay.is_visible
        # 3 rect items + 1 label = 4 items
        assert len(overlay._items) == 4

    def test_show_path_items_in_scene(self, overlay, scene):
        path = [(0, 0), (1, 0)]
        overlay.show_path(path, cost_feet=5)
        # Scene should contain the overlay items
        assert len(scene.items()) == 3  # 2 rects + 1 label

    def test_clear_removes_all(self, overlay, scene):
        overlay.show_path([(0, 0), (0, 1)], cost_feet=5)
        overlay.clear()
        assert not overlay.is_visible
        assert len(scene.items()) == 0

    def test_show_path_clears_previous(self, overlay, scene):
        overlay.show_path([(0, 0), (0, 1)], cost_feet=5)
        overlay.show_path([(1, 0), (1, 1), (1, 2)], cost_feet=10)
        # Only the new path items should remain
        assert len(overlay._items) == 4  # 3 rects + 1 label

    def test_empty_path(self, overlay, scene):
        overlay.show_path([], cost_feet=0)
        assert not overlay.is_visible
        assert len(scene.items()) == 0

    def test_single_tile_path(self, overlay, scene):
        overlay.show_path([(2, 3)], cost_feet=0)
        assert overlay.is_visible
        # 1 rect + 1 label
        assert len(overlay._items) == 2

    def test_custom_tile_size(self, overlay, scene):
        from PyQt5.QtWidgets import QGraphicsRectItem
        overlay.show_path([(0, 0)], cost_feet=0, tile_size=100)
        rects = [i for i in scene.items() if isinstance(i, QGraphicsRectItem)]
        assert len(rects) == 1
        assert rects[0].rect().width() == 100

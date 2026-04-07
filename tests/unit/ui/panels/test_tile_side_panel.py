"""Tests for TileSidePanel."""

import pytest
from unittest.mock import MagicMock

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from ui.panels.tile_side_panel import TileSidePanel
from models.tiles.tile_data import TileData, TerrainType


@pytest.fixture
def main_window():
    """Minimal MainWindow mock for TileSidePanel."""
    mw = MagicMock()
    mw.color_mode_active = False
    mw.active_color = None
    return mw


@pytest.fixture
def tile_data():
    """Real TileData for panel testing."""
    return TileData(position=(2, 3), terrain=TerrainType.FLOOR)


@pytest.fixture
def tile_data_labeled():
    """TileData with a user label."""
    td = TileData(position=(2, 3), terrain=TerrainType.FLOOR)
    td.user_label = "Test Tile"
    return td


@pytest.fixture
def tile_item():
    """Minimal QGraphicsItem-like mock."""
    return MagicMock()


class TestTileSidePanelInit:

    def test_creates_without_error(self, main_window):
        panel = TileSidePanel(main_window)
        assert panel is not None

    def test_initial_state_shows_placeholder(self, main_window):
        panel = TileSidePanel(main_window)
        assert panel.stack.currentIndex() == TileSidePanel._STACK_PLACEHOLDER

    def test_header_shows_no_tile(self, main_window):
        panel = TileSidePanel(main_window)
        assert "No tile" in panel.header_label.text()

    def test_has_three_view_buttons(self, main_window):
        panel = TileSidePanel(main_window)
        assert panel._core_btn is not None
        assert panel._entities_btn is not None
        assert panel._triggers_btn is not None


class TestTileSidePanelLoadTile:

    def test_load_tile_updates_header(self, main_window, tile_data_labeled, tile_item):
        panel = TileSidePanel(main_window)
        panel.load_tile(tile_data_labeled, tile_item, main_window)
        assert "(2, 3)" in panel.header_label.text()
        assert "Test Tile" in panel.header_label.text()

    def test_load_tile_no_label(self, main_window, tile_data, tile_item):
        panel = TileSidePanel(main_window)
        panel.load_tile(tile_data, tile_item, main_window)
        assert "(2, 3)" in panel.header_label.text()

    def test_load_tile_stores_references(self, main_window, tile_data, tile_item):
        panel = TileSidePanel(main_window)
        panel.load_tile(tile_data, tile_item, main_window)
        assert panel._tile_data is tile_data
        assert panel._tile_item is tile_item


class TestTileSidePanelSwitching:

    def test_switch_to_does_nothing_without_tile(self, main_window):
        panel = TileSidePanel(main_window)
        panel._switch_to(TileSidePanel._STACK_CORE)
        # Should stay on placeholder since no tile is loaded
        assert panel.stack.currentIndex() == TileSidePanel._STACK_PLACEHOLDER

    def test_switch_to_core_after_load(self, main_window, tile_data, tile_item):
        panel = TileSidePanel(main_window)
        panel.load_tile(tile_data, tile_item, main_window)
        panel._switch_to(TileSidePanel._STACK_CORE)
        assert panel.stack.currentIndex() == TileSidePanel._STACK_CORE

    def test_switch_to_entities(self, main_window, tile_data, tile_item):
        panel = TileSidePanel(main_window)
        panel.load_tile(tile_data, tile_item, main_window)
        panel._switch_to(TileSidePanel._STACK_ENTITIES)
        assert panel.stack.currentIndex() == TileSidePanel._STACK_ENTITIES

    def test_switch_to_triggers(self, main_window, tile_data, tile_item):
        panel = TileSidePanel(main_window)
        panel.load_tile(tile_data, tile_item, main_window)
        panel._switch_to(TileSidePanel._STACK_TRIGGERS)
        assert panel.stack.currentIndex() == TileSidePanel._STACK_TRIGGERS


class TestTileSidePanelTriggerShortcut:

    def test_open_trigger_panel_for_entity(self, main_window, tile_data, tile_item):
        panel = TileSidePanel(main_window)
        panel.load_tile(tile_data, tile_item, main_window)

        entity = MagicMock()
        entity.name = "Goblin"
        entity.triggers = []

        panel.open_trigger_panel_for_entity(entity)
        assert panel.stack.currentIndex() == TileSidePanel._STACK_TRIGGERS


class TestTileSidePanelColorButton:

    def test_color_btn_style_inactive(self, main_window):
        main_window.color_mode_active = False
        panel = TileSidePanel(main_window)
        panel.update_color_btn_style()
        # Should have no special border
        assert "22c55e" not in panel._color_btn.styleSheet()

    def test_color_btn_style_active(self, main_window):
        main_window.color_mode_active = True
        panel = TileSidePanel(main_window)
        panel.update_color_btn_style()
        # Should have green border
        assert "22c55e" in panel._color_btn.styleSheet()

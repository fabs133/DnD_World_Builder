"""Tests for CoreValuesPanel: load, save, field population."""

import pytest
from unittest.mock import MagicMock, patch

from models.tiles.tile_data import TileData, TerrainType, TileTag
from ui.panels.core_values_panel import CoreValuesPanel


@pytest.fixture(autouse=True)
def stub_event_bus(monkeypatch):
    monkeypatch.setattr(
        "core.gameCreation.event_bus.EventBus.emit",
        classmethod(lambda cls, *a, **k: None),
    )


@pytest.fixture
def tile_data():
    return TileData(
        tile_id="t_test",
        position=(3, 4),
        terrain=TerrainType.WATER,
        tags=[TileTag.BLOCKS_MOVEMENT],
        user_label="River",
        note="Deep water here",
        overlay_color="#0000FF",
        last_updated="2025-01-01T00:00:00",
    )


@pytest.fixture
def panel(qapp, tile_data):
    p = CoreValuesPanel()
    tile_item = MagicMock()
    mw = MagicMock()
    mw.undo_stack = MagicMock()
    p.load(tile_data, tile_item, mw)
    return p


class TestCoreValuesPanelLoad:

    def test_terrain_loaded(self, panel):
        assert panel.terrain_input.currentText() == "WATER"

    def test_tags_loaded(self, panel):
        assert panel.tag_checkboxes[TileTag.BLOCKS_MOVEMENT].isChecked()
        assert not panel.tag_checkboxes[TileTag.START_ZONE].isChecked()

    def test_label_loaded(self, panel):
        assert panel.label_input.text() == "River"

    def test_note_loaded(self, panel):
        assert panel.note_input.toPlainText() == "Deep water here"

    def test_overlay_loaded(self, panel):
        assert panel.overlay_input.text() == "#0000FF"

    def test_tile_id_displayed(self, panel):
        assert panel._id_label.text() == "t_test"

    def test_position_displayed(self, panel):
        assert "(3, 4)" in panel._pos_label.text()


class TestCoreValuesPanelSave:

    def test_save_writes_terrain(self, panel, tile_data):
        panel.terrain_input.setCurrentText("MOUNTAIN")
        panel.save()
        assert tile_data.terrain == TerrainType.MOUNTAIN

    def test_save_writes_tags(self, panel, tile_data):
        panel.tag_checkboxes[TileTag.BLOCKS_MOVEMENT].setChecked(False)
        panel.tag_checkboxes[TileTag.TRAP_ZONE].setChecked(True)
        panel.save()
        assert TileTag.BLOCKS_MOVEMENT not in tile_data.tags
        assert TileTag.TRAP_ZONE in tile_data.tags

    def test_save_writes_label_and_note(self, panel, tile_data):
        panel.label_input.setText("Bridge")
        panel.note_input.setPlainText("Cross here")
        panel.save()
        assert tile_data.user_label == "Bridge"
        assert tile_data.note == "Cross here"

    def test_save_updates_last_updated(self, panel, tile_data):
        panel.save()
        assert tile_data.last_updated is not None
        assert tile_data.last_updated != "2025-01-01T00:00:00"

    def test_save_pushes_undo_command(self, panel):
        panel.save()
        panel._main_window.undo_stack.push.assert_called_once()

    def test_save_no_tile_data_is_safe(self, qapp):
        p = CoreValuesPanel()
        p.save()  # Should not crash

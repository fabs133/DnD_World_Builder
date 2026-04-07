"""Tests for ZoneEditorDialog."""

import pytest
from ui.editors.zone_editor_dialog import ZoneEditorDialog
from models.tiles.tile_data import TileData, TerrainType
from models.tiles.tile_zone import TileZone


def _make_tile(num_zones=3):
    td = TileData(position=(0, 0), terrain=TerrainType.FLOOR)
    for i in range(num_zones):
        td.zones.append(TileZone(
            zone_id=f"z{i}", label=f"Zone {i}",
            connections=[f"z{j}" for j in range(num_zones) if j != i],
        ))
    return td


class TestZoneEditorDialog:

    def test_creates(self, qapp):
        td = _make_tile(2)
        dlg = ZoneEditorDialog(td)
        assert dlg is not None

    def test_zone_list_populated(self, qapp):
        td = _make_tile(3)
        dlg = ZoneEditorDialog(td)
        assert dlg._zone_list.count() == 3

    def test_add_zone(self, qapp):
        td = _make_tile(1)
        dlg = ZoneEditorDialog(td)
        dlg._add_zone()
        assert dlg._zone_list.count() == 2

    def test_remove_zone(self, qapp):
        td = _make_tile(3)
        dlg = ZoneEditorDialog(td)
        dlg._zone_list.setCurrentRow(0)
        dlg._remove_zone()
        assert dlg._zone_list.count() == 2

    def test_edit_zone_name(self, qapp):
        td = _make_tile(1)
        dlg = ZoneEditorDialog(td)
        dlg._zone_list.setCurrentRow(0)
        dlg._name_input.setText("Renamed Zone")
        dlg._on_save()
        # The save should apply the edit
        assert dlg._zones[0].label == "Renamed Zone"

    def test_save_signal(self, qapp):
        td = _make_tile(2)
        dlg = ZoneEditorDialog(td)
        saved = []
        dlg.zones_saved.connect(lambda zones: saved.append(zones))
        dlg._zone_list.setCurrentRow(0)
        dlg._on_save()
        assert len(saved) == 1
        assert len(saved[0]) == 2

    def test_cancel_no_signal(self, qapp):
        td = _make_tile(1)
        dlg = ZoneEditorDialog(td)
        saved = []
        dlg.zones_saved.connect(lambda zones: saved.append(zones))
        dlg.reject()
        assert len(saved) == 0

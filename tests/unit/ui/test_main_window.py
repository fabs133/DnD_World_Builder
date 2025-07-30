import json
import math
import tempfile
from pathlib import Path

import pytest
from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QPushButton

import ui.main_window
from ui.main_window import MainWindow
from models.tiles.square_tile_item import SquareTileItem
from models.tiles.hex_tile_item import HexTileItem

@pytest.fixture
def dummy_settings(tmp_path):
    # A minimal settings object with attributes your code might use
    class S:
        config_version = 1
        def __getitem__(self, key): return None
    return S()

@pytest.fixture
def mw(qapp, dummy_settings):
    # Create with a 2×3 square grid
    return MainWindow(dummy_settings, grid_type="square", rows=2, cols=3)

def test_initial_buttons_and_properties(mw):
    # Paint toggle is a QPushButton, initially unchecked
    pb: QPushButton = mw.paint_toggle_button
    assert isinstance(pb, QPushButton)
    assert not pb.isChecked()
    assert mw.paint_mode_active is False

    # Mode type button exists
    mtb: QPushButton = mw.mode_type_button
    assert isinstance(mtb, QPushButton)
    assert mw.paint_mode_type == "visual"

    # Trigger button starts disabled
    assert not mw.trigger_btn.isEnabled()

def test_square_grid_created(qapp, dummy_settings):
    mw2 = MainWindow(dummy_settings, grid_type="square", rows=2, cols=3)
    items = mw2.scene.items()
    # We added 2 rows × 3 cols = 6 tiles
    # QGraphicsScene.items() returns a list; ordering unimportant
    assert len([i for i in items if isinstance(i, SquareTileItem)]) == 6

def test_hex_grid_created(qapp, dummy_settings):
    mw2 = MainWindow(dummy_settings, grid_type="hex", rows=1, cols=2)
    # hex grid of 1×2 = 2 hexes
    items = mw2.scene.items()
    assert len([i for i in items if isinstance(i, HexTileItem)]) == 2

def test_toggle_paint_mode_changes_state_and_text(qapp, dummy_settings):
    mw2 = MainWindow(dummy_settings, grid_type="square", rows=1, cols=1)
    btn = mw2.paint_toggle_button
    # Turn on
    mw2.toggle_paint_mode(True)
    assert mw2.paint_mode_active is True
    # As grid_type visual, icon 🎨
    assert btn.text().startswith("🎨")
    # Turn off
    mw2.toggle_paint_mode(False)
    assert mw2.paint_mode_active is False
    assert btn.text() == "Paint Mode"

def test_toggle_paint_mode_type_updates_both_buttons(qapp, dummy_settings):
    mw2 = MainWindow(dummy_settings, grid_type="square", rows=1, cols=1)
    mtb = mw2.mode_type_button
    pb  = mw2.paint_toggle_button

    # Initially visual
    assert mw2.paint_mode_type == "visual"
    # Switch to logic
    mw2.toggle_paint_mode_type()
    assert mw2.paint_mode_type == "logic"
    assert mtb.text().startswith("🧠")
    # If paint mode is active, paint button text also updates
    mw2.toggle_paint_mode(True)
    assert pb.text().startswith("🧠")

def test_save_and_load_map(tmp_path, qapp, dummy_settings, monkeypatch):
    mw2 = MainWindow(dummy_settings, grid_type="square", rows=1, cols=1)

    # Create a temporary file
    out_file = tmp_path / "mymap.json"
    # Monkey‐patch QFileDialog to return our path
    monkeypatch.setattr("ui.main_window.QFileDialog.getSaveFileName",
                    lambda *args, **kwargs: (str(out_file), None))


    # Call save_map_dialog(); should write file
    mw2.save_map_dialog()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    # Check top‐level keys
    assert data["version"] == "1.0"
    assert "tiles" in data
    assert isinstance(data["tiles"], list)
    # Single tile
    assert len(data["tiles"]) == 1
    td = data["tiles"][0]
    assert td["position"] == (0, 0) or td["position"] == [0, 0]

    # Now test load_map_from_file: clear the scene and reload
    # Monkey‐patch QFileDialog to return our same file for load
    # But load_map_from_file takes filename arg directly:
    mw2.grid_type = "square"
    # Clear scene
    mw2.scene.clear()
    # Call load_map_from_file
    mw2.load_map_from_file(str(out_file))
    # After loading we should have 1 SquareTileItem in the scene
    loaded = mw2.scene.items()
    assert any(isinstance(i, SquareTileItem) for i in loaded)

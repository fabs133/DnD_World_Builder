import json
import math
import tempfile
from pathlib import Path

import pytest
from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QPushButton

import ui.main_window
from ui.main_window import MainWindow, hex_tile_center
from models.tiles.square_tile_item import SquareTileItem
from models.tiles.hex_tile_item import HexTileItem

@pytest.fixture
def dummy_settings(tmp_path):
    # A minimal settings object with attributes your code might use
    class S:
        config_version = 1
        def __getitem__(self, key): return None
        def get(self, key, default=None): return default
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


# --- hex_tile_center tests ---

class TestHexTileCenter:
    """Tests for the hex_tile_center positioning function."""

    def test_origin_tile(self):
        """Tile at (0, 0) should be at pixel origin."""
        x, y = hex_tile_center(0, 0, 30)
        assert x == pytest.approx(0.0)
        assert y == pytest.approx(0.0)

    def test_even_column_no_vertical_offset(self):
        """Even columns should not have a vertical offset beyond row spacing."""
        s = 30
        vert = math.sqrt(3) * s
        x, y = hex_tile_center(2, 0, s)
        assert x == pytest.approx(0.0)
        assert y == pytest.approx(2 * vert)

    def test_odd_column_has_half_vertical_offset(self):
        """Odd columns should be offset down by half the vertical spacing."""
        s = 30
        vert = math.sqrt(3) * s
        x, y = hex_tile_center(0, 1, s)
        assert x == pytest.approx(1.5 * s)
        assert y == pytest.approx(vert / 2)

    def test_horizontal_spacing(self):
        """Horizontal spacing between columns should be 1.5 * hex_size."""
        s = 30
        x0, _ = hex_tile_center(0, 0, s)
        x1, _ = hex_tile_center(0, 1, s)
        x2, _ = hex_tile_center(0, 2, s)
        assert x1 - x0 == pytest.approx(1.5 * s)
        assert x2 - x1 == pytest.approx(1.5 * s)

    def test_vertical_spacing(self):
        """Vertical spacing between rows in the same column should be sqrt(3)*s."""
        s = 30
        vert = math.sqrt(3) * s
        _, y0 = hex_tile_center(0, 0, s)
        _, y1 = hex_tile_center(1, 0, s)
        assert y1 - y0 == pytest.approx(vert)

    def test_adjacent_tiles_no_gap_no_overlap(self):
        """Adjacent hex tiles should touch exactly (distance between centers
        equals the hex width across flats = sqrt(3)*s for vertical neighbors,
        and 1.5*s horizontal + vert/2 vertical for diagonal neighbors)."""
        s = 30
        vert = math.sqrt(3) * s

        # Vertical neighbor: (0,0) -> (1,0)
        x0, y0 = hex_tile_center(0, 0, s)
        x1, y1 = hex_tile_center(1, 0, s)
        dist_vert = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
        assert dist_vert == pytest.approx(vert)

        # Diagonal neighbor: (0,0) -> (0,1)
        x2, y2 = hex_tile_center(0, 1, s)
        dist_diag = math.sqrt((x2 - x0) ** 2 + (y2 - y0) ** 2)
        # For flat-top hex, diagonal neighbor distance = 2 * s * sin(60°) = sqrt(3) * s
        assert dist_diag == pytest.approx(vert)

    def test_different_sizes(self):
        """Function should scale correctly with different hex sizes."""
        for s in [10, 20, 50, 100]:
            x, y = hex_tile_center(1, 1, s)
            assert x == pytest.approx(1.5 * s)
            assert y == pytest.approx(math.sqrt(3) * s + math.sqrt(3) * s / 2)

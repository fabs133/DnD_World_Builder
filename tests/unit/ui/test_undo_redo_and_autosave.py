# tests/unit/ui/test_undo_redo_and_autosave.py
import json
from pathlib import Path
import pytest
from PyQt5.QtCore import Qt

def test_undo_redo_tile_paint(qtbot):
    from ui.main_window import MainWindow
    from models.tiles.tile_preset import TilePreset
    from models.tiles.square_tile_item import SquareTileItem

    # Create a 1x1 grid MainWindow
    mw = MainWindow(settings={}, grid_type='square', rows=1, cols=1)
    qtbot.addWidget(mw)
    mw.show()

    # Locate the single SquareTileItem in the scene
    items = [i for i in mw.scene.items() if isinstance(i, SquareTileItem)]
    assert len(items) == 1
    tile_item = items[0]
    td = tile_item.tile_data

    # Record initial overlay_color (may be None or default)
    initial_color = td.overlay_color

    # Create a simple visual-only preset changing overlay_color
    preset = TilePreset(
        terrain=td.terrain,
        tags=td.tags,
        overlay_color='#FF0000'
    )
    mw.active_tile_preset = preset
    mw.paint_mode_active = True
    mw.paint_mode_type = 'visual'

    # Paint the tile (redo) via mouse click
    # Need to click on the view's viewport at the tile's scene position
    pos = mw.view.mapFromScene(tile_item.rect().center())
    qtbot.mouseClick(mw.view.viewport(), Qt.LeftButton, pos=pos)
    assert td.overlay_color == '#FF0000'

    # Undo should revert the overlay_color the overlay_color
    mw.undo_stack.undo()
    assert td.overlay_color == initial_color

    # Redo should reapply the overlay_color
    mw.undo_stack.redo()
    assert td.overlay_color == '#FF0000'


def test_save_map_triggers_backup(tmp_path):
    from ui.main_window import MainWindow
    from pathlib import Path

    # Initialize MainWindow with a 1x1 grid
    mw = MainWindow(settings={}, grid_type='square', rows=1, cols=1)

    # Monkey-patch backup_map to record calls
    calls = []
    mw.backup_manager.backup_map = lambda p: calls.append(p)

    # Define map path inside tmp_path
    map_path = tmp_path / 'testmap.json'

    # First save: file does not exist yet => no backup
    mw.save_map_to_file(str(map_path))
    assert map_path.exists(), "Map file should be created on first save"
    assert calls == [], "No backup should be made on initial save"

    # Second save: file exists => should invoke backup
    mw.save_map_to_file(str(map_path))
    assert calls == [Path(str(map_path))], "BackupManager.backup_map should be called once on overwrite"

    # Verify the JSON structure was written correctly
    data = json.loads(map_path.read_text(encoding='utf-8'))
    assert 'version' in data and 'tiles' in data

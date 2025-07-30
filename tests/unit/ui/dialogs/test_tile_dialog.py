import pytest
import json
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import QCheckBox, QLineEdit, QTextEdit, QComboBox
from PyQt5.QtGui import QColor
from models.tiles.tile_data import TileData, TerrainType, TileTag
import ui.dialogs.tile_dialog as td_mod
from ui.dialogs.tile_dialog import TileDialog

class DummyTileItem:
    def __init__(self):
        self.last_set = None
    def set_overlay_color(self, color):
        self.last_set = color

@pytest.fixture
def tile_data(tmp_path):
    # Create a TileData with some initial settings
    td = TileData(
        tile_id="t1",
        position=(0,0),
        terrain=TerrainType.WATER,
        tags=[TileTag.BLOCKS_MOVEMENT],
        user_label="Label",
        note="Note text",
        overlay_color="#FF0000",
        last_updated="2025-01-01T12:00:00",
        entities=[]
    )
    # Attach a dummy tile_item for preview
    td.tile_item = DummyTileItem()
    return td

@pytest.fixture
def dlg(qapp, tile_data):
    # We pass a fake main_window with an undo_stack for testing save_attributes
    class FakeMW:
        def __init__(self):
            class US:
                def __init__(self):
                    self.cmds = []
                def push(self, cmd):
                    self.cmds.append(cmd)
            self.undo_stack = US()
    fake_mw = FakeMW()
    # instantiate the dialog
    d = TileDialog(tile_data, main_window=fake_mw, tile_item=tile_data.tile_item)
    return d, tile_data, fake_mw

def test_initial_fields(dlg):
    d, td, _ = dlg
    # Terrain combo should reflect WATER
    terrain: QComboBox = d.terrain_input
    assert terrain.currentText() == "WATER"
    # Tags: only BLOCKS_MOVEMENT should be checked
    for tag, checkbox in d.tag_checkboxes.items():
        if tag is TileTag.BLOCKS_MOVEMENT:
            assert checkbox.isChecked()
        else:
            assert not checkbox.isChecked()
    # Label and Note
    label_widget: QLineEdit = d.label_input
    assert label_widget.text() == "Label"
    note_widget: QTextEdit = d.note_input
    assert note_widget.toPlainText() == "Note text"
    # Overlay color line
    overlay_line: QLineEdit = d.overlay_input
    assert overlay_line.text() == "#FF0000"
    # Last updated label
    assert d.last_updated_label.text() == "2025-01-01T12:00:00"

def test_open_color_picker_updates_input_and_preview(monkeypatch, dlg):
    d, td, _ = dlg
    # stub QColorDialog.getColor to return a valid QColor
    monkeypatch.setattr(td_mod.QColorDialog, "getColor",
                        classmethod(lambda cls, initial, parent, title: QColor("#00FF00")))
    # call the method
    d.open_color_picker()
    # input line updated
    assert d.overlay_input.text() == "#00ff00"
    # preview on tile_item updated
    assert td.tile_item.last_set.lower() == "#00ff00"

def test_save_attributes_updates_tile_and_pushes_command(dlg):
    d, td, fake_mw = dlg
    # Change several fields:
    d.terrain_input.setCurrentText("FLOOR")
    # Uncheck existing tag, check another
    d.tag_checkboxes[TileTag.BLOCKS_MOVEMENT].setChecked(False)
    d.tag_checkboxes[TileTag.BLOCKS_VISION].setChecked(True)
    d.label_input.setText("NewLabel")
    d.note_input.setPlainText("NewNote")
    d.overlay_input.setText("#ABCDEF")

    # Remember original last_updated
    before = td.last_updated
    d.save_attributes()
    # Terrain changed
    assert td.terrain == TerrainType.FLOOR
    # Tags reflect checkboxes
    assert TileTag.BLOCKS_VISION in td.tags
    assert TileTag.BLOCKS_MOVEMENT not in td.tags
    # Label & note & overlay_color
    assert td.user_label == "NewLabel"
    assert td.note == "NewNote"
    assert td.overlay_color == "#ABCDEF"
    # last_updated was set to an ISO string after before
    assert td.last_updated != before
    # Undo command was pushed
    # Verify something was pushed
    assert fake_mw.undo_stack.cmds, "Expected a TileEditCommand to be pushed"
    # Grab the first command
    cmd = fake_mw.undo_stack.cmds[0]
    # The command should hold references to original and new state
    assert isinstance(cmd.old_state, dict)
    assert isinstance(cmd.new_state, dict)

def test_edit_entities_and_triggers(monkeypatch, dlg, tile_data):
    d, td, _ = dlg
    # stub dialogs so they don't actually open UI
    class FakeEntityEditor:
        def __init__(self, td2): 
            assert td2 is td
        def exec_(self): pass
    monkeypatch.setattr(td_mod, "EntityEditorDialog", FakeEntityEditor)

    class FakeTriggerEditor:
        def __init__(self, td2):
            assert td2 is td
        def exec_(self): pass
    monkeypatch.setattr(td_mod, "TriggerEditorDialog", FakeTriggerEditor)

    # Call both
    d.edit_entities()   # should instantiate FakeEntityEditor without error
    d.edit_triggers()   # should instantiate FakeTriggerEditor

def test_entity_preview_readonly(dlg):
    d, td, _ = dlg
    # Populate entities
    # Use real GameEntity instances so .to_dict() works
    from models.entities.game_entity import GameEntity
    ent1 = GameEntity("A", "enemy")
    ent2 = GameEntity("B", "npc")
    td.entities[:] = [ent1, ent2]
    # Recreate dialog to refresh preview
    d2 = TileDialog(td)
    txt = d2.entity_preview.text()
    # Both names should appear
    assert "A" in txt and "B" in txt

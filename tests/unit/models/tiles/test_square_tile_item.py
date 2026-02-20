import pytest
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QColor, QBrush, QPen
from models.tiles.base_tile_item import BaseTileItem
import models.tiles.square_tile_item as sti_mod
from models.tiles.square_tile_item import SquareTileItem

# Dummy TileData to hold position + overlay_color
class DummyTileData:
    def __init__(self, position, overlay_color=None):
        self.position = position
        self.overlay_color = overlay_color

# Dummy event to simulate mouse presses
class DummyEvent:
    def __init__(self, button):
        self._button = button
    def button(self):
        return self._button

@pytest.fixture
def qapp(qapp):
    # ensure a QApplication exists
    return qapp

def test_inheritance_and_initial_appearance(qapp):
    td = DummyTileData(position=(1,2))
    item = SquareTileItem(0, 0, 10, tile_data=td)

    # Should be a QGraphicsRectItem and BaseTileItem
    assert isinstance(item, BaseTileItem)
    # Rectangle geometry as set
    rect = item.rect()
    assert isinstance(rect, QRectF)
    assert (rect.x(), rect.y(), rect.width(), rect.height()) == (0.0, 0.0, 10.0, 10.0)

    # Initial brush and pen
    assert isinstance(item.brush(), QBrush)
    assert item.brush().color() == QColor(200, 200, 200)
    assert item.pen().color() == QColor(Qt.black)

def test_hover_events_pen_changes(qapp):
    td = DummyTileData(position=(0,0), overlay_color="#ABCDEF")
    # No editor_window => paint_mode_active False
    item = SquareTileItem(0, 0, 5, tile_data=td, editor_window=None)

    # hover enter → black pen
    item.hoverEnterEvent(None)
    assert item.pen().color() == QColor(Qt.black)

    # hover leave → black pen + overlay brush
    # change pen first
    item.setPen(QPen(Qt.red, 2))
    item.hoverLeaveEvent(None)
    assert item.pen().color() == QColor(Qt.black)
    # brush should show overlay color
    assert item.brush().color() == QColor("#ABCDEF")

    # With editor_window.paint_mode_active = True
    class ED:
        paint_mode_active = True
    item.editor_window = ED()
    # hover enter → blue thick pen
    item.hoverEnterEvent(None)
    pen = item.pen()
    assert pen.color() == QColor(Qt.blue)
    assert pen.width() == 3

def test_left_click_paint_mode_pushes_command_and_applies(monkeypatch, qapp):
    # Prepare dummy tile data
    td = DummyTileData(position=(9,9), overlay_color=None)

    # Stub out TileEditCommand in the module to capture args
    recorded = {}
    class DummyCommand:
        def __init__(self, tile_data, preset, logic, description):
            recorded['args'] = (tile_data, preset, logic, description)
        def redo(self):
            pass
        def __repr__(self):
            return "<DummyCommand>"
    monkeypatch.setattr(sti_mod, "TileEditCommand", DummyCommand)

    # Prepare a dummy preset
    class DummyPreset:
        pass

    preset = DummyPreset()

    # Dummy undo stack to capture push()
    class UndoStack:
        def __init__(self):
            self.pushed = []
        def push(self, cmd):
            self.pushed.append(cmd)

    undo = UndoStack()

    # Editor window stub
    class ED:
        paint_mode_active = True
        paint_mode_type = "visual"   # visual => logic=False
        active_tile_preset = preset
        undo_stack = undo

    item = SquareTileItem(0, 0, 8, tile_data=td, editor_window=ED())

    # Simulate left‐click
    evt = DummyEvent(Qt.LeftButton)
    item.mousePressEvent(evt)

    # 1) Command was constructed with correct args
    td_arg, preset_arg, logic_arg, desc = recorded['args']
    assert td_arg is td
    assert preset_arg is preset
    assert logic_arg is False
    assert desc == f"Paint tile {td.position}"

    # 2) UndoStack.push called with our DummyCommand instance
    assert len(undo.pushed) == 1
    assert isinstance(undo.pushed[0], DummyCommand)

def test_left_click_no_paint_mode_does_nothing(monkeypatch, qapp):
    td = DummyTileData(position=(5,5), overlay_color=None)
    # Editor window inactive
    class ED:
        paint_mode_active = False
    item = SquareTileItem(0, 0, 6, tile_data=td, editor_window=ED())
    evt = DummyEvent(Qt.LeftButton)
    # No exceptions; no change to overlay_color
    item.mousePressEvent(evt)
    assert td.overlay_color is None

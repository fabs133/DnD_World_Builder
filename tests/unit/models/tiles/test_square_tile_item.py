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
    # No editor_window => color_mode_active False
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

    # With editor_window.color_mode_active = True
    class ED:
        color_mode_active = True
    item.editor_window = ED()
    # hover enter → green thick pen
    item.hoverEnterEvent(None)
    pen = item.pen()
    assert pen.color() == QColor("#22c55e")
    assert pen.width() == 3

def test_left_click_color_mode_pushes_command(monkeypatch, qapp):
    # Prepare dummy tile data with tile_id for ColorPaintCommand
    td = DummyTileData(position=(9,9), overlay_color=None)
    td.tile_id = "9_9"

    # Stub out ColorPaintCommand in the module to capture args
    recorded = {}
    class DummyCommand:
        def __init__(self, tile_data, new_color):
            recorded['args'] = (tile_data, new_color)
        def redo(self):
            pass
        def __repr__(self):
            return "<DummyCommand>"
    monkeypatch.setattr(sti_mod, "ColorPaintCommand", DummyCommand)

    # Dummy undo stack to capture push()
    class UndoStack:
        def __init__(self):
            self.pushed = []
        def push(self, cmd):
            self.pushed.append(cmd)

    undo = UndoStack()

    # Editor window stub with color mode active
    class ED:
        color_mode_active = True
        active_color = "#FF0000"
        undo_stack = undo

    item = SquareTileItem(0, 0, 8, tile_data=td, editor_window=ED())

    # Simulate left-click
    evt = DummyEvent(Qt.LeftButton)
    item.mousePressEvent(evt)

    # 1) ColorPaintCommand was constructed with correct args
    td_arg, color_arg = recorded['args']
    assert td_arg is td
    assert color_arg == "#FF0000"

    # 2) UndoStack.push called with our DummyCommand instance
    assert len(undo.pushed) == 1
    assert isinstance(undo.pushed[0], DummyCommand)

def test_left_click_no_color_mode_calls_select_tile(monkeypatch, qapp):
    td = DummyTileData(position=(5,5), overlay_color=None)
    selected = []

    # Editor window with color mode off; select_tile records calls
    class ED:
        color_mode_active = False
        def select_tile(self, tile):
            selected.append(tile)

    item = SquareTileItem(0, 0, 6, tile_data=td, editor_window=ED())
    evt = DummyEvent(Qt.LeftButton)
    item.mousePressEvent(evt)

    # select_tile should have been called with the tile item
    assert len(selected) == 1
    assert selected[0] is item
    # overlay_color unchanged
    assert td.overlay_color is None

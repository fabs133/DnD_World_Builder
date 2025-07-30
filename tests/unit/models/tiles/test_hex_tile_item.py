import math
import pytest
from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QColor, QBrush, QPen, QPolygonF
from models.tiles.base_tile_item import BaseTileItem
from models.tiles.tile_data import TileData
from models.tiles.hex_tile_item import HexTileItem

@pytest.fixture
def qapp(qapp):
    # Ensure a QApplication is available (pytest-qt’s qapp fixture)
    return qapp

def make_tile(center=(0, 0), size=10, overlay_color=None):
    # Create a minimal TileData with position and overlay_color
    td = TileData(position=center, overlay_color=overlay_color)
    return td

def test_inheritance_and_initial_brush_pen(qapp):
    center = QPointF(5, 7)
    size = 12
    td = make_tile(center=(5,7), size=size) if False else make_tile(center=(5,7))
    item = HexTileItem(center, size, tile_data=td)

    # Should inherit from both QGraphicsPolygonItem and BaseTileItem
    assert isinstance(item, BaseTileItem)
    assert item.size == size
    assert item.center == center

    # Initial brush color is RGB(200,200,200)
    brush = item.brush()
    assert isinstance(brush, QBrush)
    assert brush.color() == QColor(200, 200, 200)

    # Initial pen is solid black
    pen = item.pen()
    assert isinstance(pen, QPen)
    assert pen.color() == QColor(Qt.black)

def test_create_hexagon_shape(qapp):
    center = QPointF(0, 0)
    size = 10
    td = make_tile(center=(0,0))
    item = HexTileItem(center, size, tile_data=td)

    poly: QPolygonF = item.polygon()
    assert isinstance(poly, QPolygonF)
    # Should have exactly 6 points
    assert poly.count() == 6

    # Check first point is at angle -30°
    expected_x = size * math.cos(math.radians(-30))
    expected_y = size * math.sin(math.radians(-30))
    p0 = poly.at(0)
    assert pytest.approx(p0.x(), rel=1e-3) == expected_x
    assert pytest.approx(p0.y(), rel=1e-3) == expected_y

def test_hover_enter_event_changes_pen(qapp, qtbot):
    center = QPointF(0,0)
    size = 5
    td = make_tile(center=(0,0))
    # Editor inactive
    item = HexTileItem(center, size, tile_data=td, editor_window=None)
    # Simulate hover enter with no editor_window
    item.hoverEnterEvent(None)
    assert item.pen().color() == QColor(Qt.black)
    # Now simulate an editor_window in paint mode
    class Editor:
        paint_mode_active = True
    ed = Editor()
    item.editor_window = ed
    # On hover enter, should turn blue, width 3
    item.hoverEnterEvent(None)
    pen = item.pen()
    assert pen.color() == QColor(Qt.blue)
    assert pen.width() == 3

def test_hover_leave_event_resets_pen_and_updates_overlay(qapp):
    center = QPointF(0,0)
    size = 5
    td = make_tile(center=(0,0), overlay_color="#ABCDEF")
    item = HexTileItem(center, size, tile_data=td)
    # Change pen to something else
    item.setPen(QPen(Qt.red, 2))
    # Simulate hover leave
    item.hoverLeaveEvent(None)
    # Pen should be reset to black
    assert item.pen().color() == QColor(Qt.black)
    # Brush should reflect overlay_color
    brush = item.brush()
    assert brush.color() == QColor("#ABCDEF")

def test_set_and_update_overlay_color(qapp):
    center = QPointF(0,0)
    size = 5
    td = make_tile(center=(0,0))
    item = HexTileItem(center, size, tile_data=td)
    # No overlay_color initially => default "#CCCCCC"
    item.update_overlay_color()
    assert item.brush().color() == QColor("#CCCCCC")
    # Now set overlay
    item.set_overlay_color("#123456")
    assert td.overlay_color == "#123456"
    # Brush updated
    assert item.brush().color() == QColor("#123456")

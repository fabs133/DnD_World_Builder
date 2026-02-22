# tests/unit/ui/interactions/test_square_tile_item_interactions.py
import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView
from models.tiles.square_tile_item import SquareTileItem


@pytest.fixture
def tile_setup(qtbot, mocker):
    # Patch ColorPaintCommand so it doesn't actually mutate tile data
    mocker.patch('models.tiles.square_tile_item.ColorPaintCommand', autospec=True)

    # Setup a mock editor window with color mode active
    mock_editor = mocker.Mock()
    mock_editor.color_mode_active = True
    mock_editor.active_color = '#FF0000'

    # Dummy tile_data with overlay_color and position
    tile_data = mocker.Mock()
    tile_data.overlay_color = '#AAAAAA'
    tile_data.position = (5, 5)
    tile_data.background_image = None

    # Create the SquareTileItem and wrap in a QGraphicsScene/View
    tile = SquareTileItem(0, 0, 50, tile_data=tile_data, editor_window=mock_editor)
    scene = QGraphicsScene()
    scene.addItem(tile)
    view = QGraphicsView(scene)
    qtbot.addWidget(view)
    view.show()

    return tile, mock_editor, tile_data, view


def test_hover_changes_pen(tile_setup):
    tile, editor, data, view = tile_setup
    # Directly invoke hoverEnterEvent (event object isn't used in logic)
    tile.hoverEnterEvent(None)

    pen = tile.pen()
    # Expect pen to be green and width 3 in color mode
    assert pen.color().name() == QColor("#22c55e").name()
    assert pen.width() == 3


def test_left_click_color_mode_pushes_command(tile_setup, qtbot):
    from models.tiles.square_tile_item import ColorPaintCommand
    tile, editor, data, view = tile_setup
    pos = view.mapFromScene(tile.rect().center())
    qtbot.mouseClick(view.viewport(), Qt.LeftButton, pos=pos)

    # ColorPaintCommand should be constructed with tile_data and active_color
    ColorPaintCommand.assert_called_once_with(data, editor.active_color)
    editor.undo_stack.push.assert_called_once()


def test_left_click_no_color_mode_calls_select_tile(tile_setup, qtbot):
    tile, editor, data, view = tile_setup
    # Disable color mode
    editor.color_mode_active = False
    pos = view.mapFromScene(tile.rect().center())
    qtbot.mouseClick(view.viewport(), Qt.LeftButton, pos=pos)

    # select_tile should have been called instead
    editor.select_tile.assert_called_once_with(tile)


def test_right_click_color_mode_samples_color(tile_setup, qtbot):
    tile, editor, data, view = tile_setup
    data.overlay_color = '#123456'
    pos = view.mapFromScene(tile.rect().center())
    qtbot.mouseClick(view.viewport(), Qt.RightButton, pos=pos)

    # active_color should be updated to the tile's overlay_color
    assert editor.active_color == '#123456'

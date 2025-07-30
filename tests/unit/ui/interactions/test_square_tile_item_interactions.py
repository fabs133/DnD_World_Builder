# tests/unit/ui/interactions/test_square_tile_item_interactions.py
import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView
from models.tiles.square_tile_item import SquareTileItem
from models.tiles.tile_preset import TilePreset

@pytest.fixture
def tile_setup(qtbot, mocker):
    # Patch TilePreset.from_tile_data before instantiation
    mocker.patch('models.tiles.tile_preset.TilePreset.from_tile_data', autospec=True)

    # Setup a mock editor window
    mock_editor = mocker.Mock()
    mock_editor.paint_mode_active = True
    mock_editor.paint_mode_type = 'visual'
    mock_editor.active_tile_preset = mocker.Mock(spec=TilePreset)

    # Dummy tile_data with overlay_color and position
    tile_data = mocker.Mock()
    tile_data.overlay_color = '#AAAAAA'
    tile_data.position = (5, 5)

    # Create the SquareTileItem and wrap in a QGraphicsScene/View
    tile = SquareTileItem(0, 0, 50, tile_data=tile_data, editor_window=mock_editor)
    scene = QGraphicsScene()
    scene.addItem(tile)
    view = QGraphicsView(scene)
    qtbot.addWidget(view)
    view.show()

    return tile, mock_editor, tile_data, view


from PyQt5.QtWidgets import QGraphicsSceneHoverEvent
from PyQt5.QtCore import QEvent

def test_hover_changes_pen(tile_setup):
    tile, editor, data, view = tile_setup
    # Simulate hover enter event directly since QGraphicsView/QTest won't dispatch QGraphicsSceneHoverEvent
    # Directly invoke hoverEnterEvent (event object isn't used in logic)
    tile.hoverEnterEvent(None)

    pen = tile.pen()
    # Expect pen to be blue and width 3 in paint mode
    assert pen.color().name() == QColor(Qt.blue).name()
    assert pen.width() == 3


def test_left_click_applies_visual_preset(tile_setup, qtbot):
    tile, editor, data, view = tile_setup
    pos = view.mapFromScene(tile.rect().center())
    qtbot.mouseClick(view.viewport(), Qt.LeftButton, pos=pos)

    editor.active_tile_preset.apply_to.assert_called_once_with(data, logic=False)
    # Ensure overlay brush updated
    assert tile.brush().color().name() == QColor(data.overlay_color).name()


def test_left_click_applies_logic_preset(tile_setup, qtbot):
    tile, editor, data, view = tile_setup
    editor.paint_mode_type = 'logic'
    pos = view.mapFromScene(tile.rect().center())
    qtbot.mouseClick(view.viewport(), Qt.LeftButton, pos=pos)

    editor.active_tile_preset.apply_to.assert_called_once_with(data, logic=True)


def test_right_click_samples_preset(tile_setup, qtbot):
    tile, editor, data, view = tile_setup
    pos = view.mapFromScene(tile.rect().center())
    qtbot.mouseClick(view.viewport(), Qt.RightButton, pos=pos)

    # TilePreset.from_tile_data should have been called
    TilePreset.from_tile_data.assert_called_once_with(data)
    # The editor_window.active_tile_preset should update to the returned value
    assert editor.active_tile_preset == TilePreset.from_tile_data.return_value
from core.logger import app_logger
from PyQt5.QtWidgets import QGraphicsRectItem
from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPen, QPixmap
from models.tiles.base_tile_item import BaseTileItem
from ui.commands.tile_edit_command import TileEditCommand

class SquareTileItem(QGraphicsRectItem, BaseTileItem):
    """
    A QGraphicsRectItem representing a square tile in the editor.

    Inherits from QGraphicsRectItem and BaseTileItem, and handles painting,
    hover, and mouse events for tile editing.

    :param x: The x-coordinate of the tile.
    :type x: float
    :param y: The y-coordinate of the tile.
    :type y: float
    :param size: The size (width and height) of the square tile.
    :type size: float
    :param tile_data: The data associated with this tile.
    :type tile_data: dict, optional
    :param editor_window: Reference to the editor window.
    :type editor_window: QWidget, optional
    """
    def __init__(self, x, y, size, tile_data=None, editor_window=None):
        """
        Initialize the SquareTileItem.

        See class docstring for parameter details.
        """
        super().__init__()
        self.tile_data = tile_data or {}
        self.editor_window = editor_window
        self.setRect(QRectF(x, y, size, size))
        self.setBrush(QBrush(QColor(200, 200, 200)))
        self.setPen(QPen(Qt.black))
        self.setAcceptHoverEvents(True)
        self._bg_pixmap = None
        self._load_background_image()

    def hoverEnterEvent(self, event):
        """
        Handle the hover enter event.

        Highlights the tile if paint mode is active.

        :param event: The hover event.
        :type event: QGraphicsSceneHoverEvent
        """
        if self.editor_window and self.editor_window.paint_mode_active:
            self.setPen(QPen(Qt.blue, 3))
        else:
            self.setPen(QPen(Qt.black))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """
        Handle the hover leave event.

        Resets the tile's pen and overlay color.

        :param event: The hover event.
        :type event: QGraphicsSceneHoverEvent
        """
        self.setPen(QPen(Qt.black))
        self.update_overlay_color()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        """
        Handle mouse press events for painting or sampling tiles.

        :param event: The mouse event.
        :type event: QGraphicsSceneMouseEvent
        """
        if event.button() == Qt.LeftButton:
            if self.editor_window and self.editor_window.paint_mode_active:
                preset = self.editor_window.active_tile_preset
                if preset:
                    logic = (self.editor_window.paint_mode_type != "visual")
                    cmd = TileEditCommand(self.tile_data, preset, logic,
                        description=f"Paint tile {self.tile_data.position}")
                    self.editor_window.undo_stack.push(cmd)

        elif event.button() == Qt.RightButton:
            if self.editor_window and self.editor_window.paint_mode_active:
                from models.tiles.tile_preset import TilePreset
                self.editor_window.active_tile_preset = TilePreset.from_tile_data(self.tile_data)
                app_logger.debug(f"[Paint Mode] Sampled preset from tile at {self.tile_data.position}")
            else:
                self.handle_right_click(event)

    def handle_hover_enter(self, event):
        """
        Custom handler for hover enter, changes brush color.

        :param event: The hover event.
        :type event: QGraphicsSceneHoverEvent
        """
        self.setBrush(QBrush(QColor(180, 180, 250)))

    def handle_hover_leave(self, event):
        """
        Custom handler for hover leave, updates overlay color.

        :param event: The hover event.
        :type event: QGraphicsSceneHoverEvent
        """
        self.update_overlay_color()

    def handle_right_click(self, event):
        """
        Handle right-click event to open the tile dialog.

        :param event: The mouse event.
        :type event: QGraphicsSceneMouseEvent
        """
        from ui.dialogs.tile_dialog import TileDialog
        dialog = TileDialog(self.tile_data)
        dialog.exec_()

    def set_overlay_color(self, hex_color):
        """
        Set the overlay color of the tile.

        :param hex_color: The color in hex format (e.g., '#CCCCCC').
        :type hex_color: str
        """
        self.tile_data.overlay_color = hex_color
        self.update_overlay_color()

    def update_overlay_color(self):
        """
        Update the brush color based on the tile's overlay color.
        """
        color = QColor(self.tile_data.overlay_color or "#CCCCCC")
        self.setBrush(QBrush(color))

    def _load_background_image(self):
        """
        Load the background image from tile_data if set.
        """
        bg = getattr(self.tile_data, "background_image", None)
        if bg:
            pixmap = QPixmap(bg)
            if not pixmap.isNull():
                self._bg_pixmap = pixmap
                return
        self._bg_pixmap = None

    def reload_background_image(self):
        """
        Reload the background image (call after changing tile_data.background_image).
        """
        self._load_background_image()
        self.update()

    def paint(self, painter, option, widget=None):
        """
        Paint the tile, rendering a background image if one is set.

        :param painter: The QPainter to draw with.
        :param option: Style options.
        :param widget: The widget being painted on.
        """
        if self._bg_pixmap:
            rect = self.rect()
            painter.drawPixmap(
                rect.toRect(),
                self._bg_pixmap.scaled(
                    int(rect.width()), int(rect.height()),
                    Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                ),
            )
            painter.setPen(self.pen())
            painter.drawRect(rect)
        else:
            super().paint(painter, option, widget)

from core.logger import app_logger
from PyQt5.QtWidgets import QGraphicsRectItem
from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPen, QPixmap, QImageReader
from models.tiles.base_tile_item import BaseTileItem
from ui.commands.tile_edit_command import TileEditCommand
from ui.commands.color_paint_command import ColorPaintCommand

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

        Shows a green border when color mode is active, otherwise default.

        :param event: The hover event.
        :type event: QGraphicsSceneHoverEvent
        """
        if self.editor_window and self.editor_window.color_mode_active:
            self.setPen(QPen(QColor("#22c55e"), 3))
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
        Handle mouse press events.

        Left-click in color mode paints the tile; otherwise selects it.
        Right-click in color mode samples the tile's color; otherwise also selects.

        :param event: The mouse event.
        :type event: QGraphicsSceneMouseEvent
        """
        if event.button() == Qt.LeftButton:
            if self.editor_window and self.editor_window.color_mode_active:
                cmd = ColorPaintCommand(self.tile_data, self.editor_window.active_color)
                self.editor_window.undo_stack.push(cmd)
            else:
                if self.editor_window:
                    self.editor_window.select_tile(self)

        elif event.button() == Qt.RightButton:
            if self.editor_window and self.editor_window.color_mode_active:
                self.editor_window.active_color = (
                    self.tile_data.overlay_color or "#CCCCCC"
                )
                app_logger.debug(
                    f"[Color Mode] Sampled color {self.editor_window.active_color} "
                    f"from tile {self.tile_data.position}"
                )
            else:
                if self.editor_window:
                    self.editor_window.select_tile(self)

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
        dialog = TileDialog(self.tile_data, main_window=self.editor_window, tile_item=self)
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
        Load the background image from tile_data, respecting EXIF orientation.
        """
        bg = getattr(self.tile_data, "background_image", None)
        if bg:
            reader = QImageReader(bg)
            reader.setAutoTransform(True)
            image = reader.read()
            if not image.isNull():
                self._bg_pixmap = QPixmap.fromImage(image)
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

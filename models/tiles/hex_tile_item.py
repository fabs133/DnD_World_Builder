import math
from PyQt5.QtWidgets import QGraphicsPolygonItem
from PyQt5.QtGui import QBrush, QPen, QColor, QPolygonF
from PyQt5.QtCore import Qt, QPointF
from models.tiles.base_tile_item import BaseTileItem
from models.tiles.tile_data import TileData

class HexTileItem(QGraphicsPolygonItem, BaseTileItem):
    """
    A QGraphicsPolygonItem representing a hexagonal tile in the map editor.

    This class manages the visual representation and interaction logic for a single hex tile,
    including painting, sampling presets, and displaying dialogs for editing tile data.

    Attributes
    ----------
    tile_data : dict
        Data associated with the tile, such as position and overlay color.
    editor_window : QWidget or None
        Reference to the editor window, used for accessing paint mode and presets.
    size : float
        The radius of the hexagon.
    center : QPointF
        The center point of the hexagon.
    """

    def __init__(self, center, size, tile_data=None, editor_window=None):
        """
        Initialize a HexTileItem.

        Parameters
        ----------
        center : QPointF
            The center position of the hex tile.
        size : float
            The radius of the hex tile.
        tile_data : dict, optional
            Initial data for the tile (default is None).
        editor_window : QWidget, optional
            Reference to the editor window (default is None).
        """
        super().__init__()
        self.tile_data = tile_data or {}
        self.editor_window = editor_window
        self.size = size
        self.center = center
        self.setPolygon(self.create_hexagon())
        self.setBrush(QBrush(QColor(200, 200, 200)))
        self.setPen(QPen(Qt.black))
        self.setAcceptHoverEvents(True)

    def create_hexagon(self):
        """
        Create a QPolygonF representing a regular hexagon centered at self.center.

        Returns
        -------
        QPolygonF
            The polygon representing the hexagon.
        """
        points = []
        for i in range(6):
            angle_deg = 60 * i - 30
            angle_rad = math.radians(angle_deg)
            x = self.center.x() + self.size * math.cos(angle_rad)
            y = self.center.y() + self.size * math.sin(angle_rad)
            points.append(QPointF(x, y))
        return QPolygonF(points)

    def hoverEnterEvent(self, event):
        """
        Handle the hover enter event.

        Highlights the tile border if paint mode is active.

        Parameters
        ----------
        event : QGraphicsSceneHoverEvent
            The hover event.
        """
        if self.editor_window and self.editor_window.paint_mode_active:
            self.setPen(QPen(Qt.blue, 3))
        else:
            self.setPen(QPen(Qt.black))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """
        Handle the hover leave event.

        Resets the tile border and updates overlay color.

        Parameters
        ----------
        event : QGraphicsSceneHoverEvent
            The hover event.
        """
        self.setPen(QPen(Qt.black))
        self.update_overlay_color()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        """
        Handle mouse press events for painting or sampling presets.

        Parameters
        ----------
        event : QGraphicsSceneMouseEvent
            The mouse event.
        """
        if event.button() == Qt.LeftButton:
            if self.editor_window and self.editor_window.paint_mode_active:
                preset = self.editor_window.active_tile_preset
                if preset:
                    if self.editor_window.paint_mode_type == "visual":
                        preset.apply_to(self.tile_data, logic=False)
                    else:
                        preset.apply_to(self.tile_data, logic=True)
                    self.set_overlay_color(self.tile_data.overlay_color)

        elif event.button() == Qt.RightButton:
            if self.editor_window and self.editor_window.paint_mode_active:
                from models.tiles.tile_preset import TilePreset
                self.editor_window.active_tile_preset = TilePreset.from_tile_data(self.tile_data)
                print("[Paint Mode] Sampled preset from tile at", self.tile_data.position)
            else:
                self.handle_right_click(event)

    def handle_hover_enter(self, event):
        """
        Custom handler for hover enter event.

        Parameters
        ----------
        event : QGraphicsSceneHoverEvent
            The hover event.
        """
        self.setBrush(QBrush(QColor(180, 180, 250)))

    def handle_hover_leave(self, event):
        """
        Custom handler for hover leave event.

        Parameters
        ----------
        event : QGraphicsSceneHoverEvent
            The hover event.
        """
        self.update_overlay_color()

    def handle_right_click(self, event):
        """
        Handle right-click event to open the tile dialog.

        Parameters
        ----------
        event : QGraphicsSceneMouseEvent
            The mouse event.
        """
        from ui.dialogs.tile_dialog import TileDialog
        dialog = TileDialog(self.tile_data)
        dialog.exec_()

    def set_overlay_color(self, hex_color):
        """
        Set the overlay color of the tile.

        Parameters
        ----------
        hex_color : str
            The hex color string to set as the overlay color.
        """
        self.tile_data.overlay_color = hex_color
        self.update_overlay_color()

    def update_overlay_color(self):
        """
        Update the brush color of the tile based on the overlay color in tile_data.
        """
        color = QColor(self.tile_data.overlay_color or "#CCCCCC")
        self.setBrush(QBrush(color))

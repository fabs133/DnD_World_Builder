import json

from core.logger import app_logger
from PyQt5.QtWidgets import QGraphicsRectItem
from PyQt5.QtCore import QRectF, Qt, QByteArray
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
        self.setAcceptDrops(True)
        self._hovered = False
        self._selected_highlight = False
        self._bg_pixmap = None
        self._load_background_image()

    def hoverEnterEvent(self, event):
        """
        Handle the hover enter event.

        Shows a green border when color mode is active, otherwise
        sets hover flag for gold overlay in paint().
        """
        if self.editor_window and self.editor_window.color_mode_active:
            self.setPen(QPen(QColor("#22c55e"), 3))
        else:
            self._hovered = True
            self.setCursor(Qt.PointingHandCursor)
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """
        Handle the hover leave event.

        Clears hover flag, resets pen and overlay color.
        """
        self._hovered = False
        self.unsetCursor()
        self.setPen(QPen(Qt.black))
        self.update_overlay_color()
        self.update()
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
                self._show_context_menu(event)

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def _show_context_menu(self, event) -> None:
        from PyQt5.QtWidgets import QMenu
        menu = QMenu()
        menu.addAction("Edit Tile...", self._open_tile_dialog)
        menu.addAction("Add to Timeline", self._add_to_timeline)
        menu.addSeparator()
        menu.addAction("Simulate Combat...", self._open_simulation)
        menu.exec_(event.screenPos())

    def _open_tile_dialog(self) -> None:
        from ui.dialogs.tile_dialog import TileDialog
        dialog = TileDialog(self.tile_data, main_window=self.editor_window, tile_item=self)
        dialog.exec_()

    def _add_to_timeline(self) -> None:
        if self.editor_window and hasattr(self.editor_window, "_on_tile_add_to_timeline"):
            self.editor_window._on_tile_add_to_timeline(self.tile_data)

    def _open_simulation(self) -> None:
        if self.editor_window and hasattr(self.editor_window, "_open_simulation_for_tile"):
            self.editor_window._open_simulation_for_tile(self.tile_data)

    # ------------------------------------------------------------------
    # Drag-and-drop support (assets and entities from palette panels)
    # ------------------------------------------------------------------

    _ACCEPTED_MIMES = {"application/x-dnd-asset", "application/x-dnd-entity"}

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if any(mime.hasFormat(m) for m in self._ACCEPTED_MIMES):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        mime = event.mimeData()

        # Asset drop (image or audio from AssetManagerPanel)
        if mime.hasFormat("application/x-dnd-asset"):
            try:
                raw = bytes(mime.data("application/x-dnd-asset")).decode()
                data = json.loads(raw)
                asset_path = data.get("path", "")
                asset_type = data.get("type", "")

                if asset_type == "image":
                    self.tile_data.background_image = asset_path
                    self.reload_background_image()
                    app_logger.info(f"[Tile] Background image set: {asset_path}")
                elif asset_type == "audio":
                    self.tile_data.ambient_audio = asset_path
                    app_logger.info(f"[Tile] Ambient audio set: {asset_path}")

                event.acceptProposedAction()
            except Exception as exc:
                app_logger.warning(f"[Tile] Asset drop failed: {exc}")
                event.ignore()
            return

        # Entity drop (from EntityPalettePanel)
        if mime.hasFormat("application/x-dnd-entity"):
            try:
                raw = bytes(mime.data("application/x-dnd-entity")).decode()
                entity_data = json.loads(raw)
                from models.entities.game_entity import GameEntity
                entity = GameEntity.from_dict(entity_data)
                self.tile_data.add_entity(entity)
                app_logger.info(f"[Tile] Entity dropped: {entity.name}")
                event.acceptProposedAction()
            except Exception as exc:
                app_logger.warning(f"[Tile] Entity drop failed: {exc}")
                event.ignore()
            return

        event.ignore()

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

    # Terrain → default color for tiles without explicit overlay
    _TERRAIN_DEFAULTS = {
        "GRASS": "#649C4B", "WATER": "#375FAA", "MOUNTAIN": "#8C8278",
        "FLOOR": "#968C7D", "WALL": "#37322D", "SAND": "#BEAF82",
        "SWAMP": "#4B6441",
    }

    def update_overlay_color(self):
        """
        Update the brush color based on overlay color or terrain type.
        """
        if self.tile_data.overlay_color:
            color = QColor(self.tile_data.overlay_color)
        else:
            terrain_name = ""
            if hasattr(self.tile_data, "terrain"):
                t = self.tile_data.terrain
                terrain_name = t.name if hasattr(t, "name") else str(t).upper()
            hex_color = self._TERRAIN_DEFAULTS.get(terrain_name, "#CCCCCC")
            color = QColor(hex_color)
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

    def set_selected_highlight(self, selected: bool) -> None:
        """Set whether this tile shows the selection indicator."""
        if self._selected_highlight != selected:
            self._selected_highlight = selected
            self.update()

    def paint(self, painter, option, widget=None):
        """
        Paint the tile, rendering a background image if one is set,
        plus hover overlay and selection border.
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

        # Hover overlay: subtle gold tint
        if self._hovered:
            hover_color = QColor(200, 170, 60, 35)
            painter.fillRect(self.rect(), hover_color)

        # Selection border: accent-colored inset border
        if self._selected_highlight:
            select_color = QColor(122, 32, 13, 200)  # crimson
            pen = QPen(select_color, 2.5)
            pen.setJoinStyle(Qt.MiterJoin)
            inset = self.rect().adjusted(1.5, 1.5, -1.5, -1.5)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(inset)

        # Entity indicators: small colored dots for entities on this tile
        entities = getattr(self.tile_data, "entities", [])
        if entities and isinstance(entities, list) and len(entities) > 0:
            rect = self.rect()
            dot_size = max(4, int(rect.width() * 0.15))
            x_start = int(rect.x() + 3)
            y_pos = int(rect.y() + rect.height() - dot_size - 2)
            type_colors = {
                "player": QColor(60, 100, 200),
                "enemy": QColor(200, 60, 60),
                "npc": QColor(60, 180, 100),
                "ally": QColor(60, 180, 60),
                "object": QColor(180, 160, 60),
            }
            for i, ent in enumerate(entities[:4]):  # max 4 dots
                etype = ""
                if isinstance(ent, dict):
                    etype = ent.get("entity_type", "")
                else:
                    etype = str(getattr(ent, "entity_type", ""))
                color = type_colors.get(etype.lower(), QColor(140, 140, 140))
                painter.setPen(QPen(QColor(20, 20, 20), 1))
                painter.setBrush(QBrush(color))
                painter.drawEllipse(
                    x_start + i * (dot_size + 2), y_pos,
                    dot_size, dot_size,
                )

from PyQt5.QtWidgets import QUndoCommand


class ColorPaintCommand(QUndoCommand):
    """
    QUndoCommand that records and undoes a single overlay-color paint operation.

    :param tile_data: The tile data to modify.
    :param new_color: The hex color string to apply.
    """

    def __init__(self, tile_data, new_color):
        super().__init__(f"Color Tile {tile_data.tile_id}")
        self.tile_data = tile_data
        self.old_color = tile_data.overlay_color
        self.new_color = new_color

    def redo(self):
        self.tile_data.overlay_color = self.new_color
        self._refresh()
        self._emit_tile_modified()

    def undo(self):
        self.tile_data.overlay_color = self.old_color
        self._refresh()
        self._emit_tile_modified()

    def _emit_tile_modified(self):
        from core.gameCreation.event_bus import EventBus
        from core.events import TILE_MODIFIED
        EventBus.emit(TILE_MODIFIED, {
            "position": self.tile_data.position,
            "tile_id": self.tile_data.tile_id,
        })

    def _refresh(self):
        tile_item = getattr(self.tile_data, "tile_item", None)
        if tile_item:
            tile_item.set_overlay_color(self.tile_data.overlay_color or "#CCCCCC")

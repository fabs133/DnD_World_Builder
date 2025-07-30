from PyQt5.QtWidgets import QUndoCommand

class TileEditCommand(QUndoCommand):
    """
    QUndoCommand for editing a tile's properties.

    This command encapsulates the changes made to a tile, allowing undo and redo operations
    by storing the old and new states of the tile.

    :param tile_data: The TileData instance representing the tile being edited.
    :type tile_data: TileData
    :param old_state: The previous state of the tile, as a dictionary.
    :type old_state: dict
    :param new_state: The new state of the tile, as a dictionary.
    :type new_state: dict
    :param tile_item: The graphical item associated with the tile, if any.
    :type tile_item: QGraphicsItem or None
    """

    def __init__(self, tile_data, old_state, new_state, tile_item=None):
        """
        Initialize the TileEditCommand.

        :param tile_data: The TileData instance representing the tile being edited.
        :type tile_data: TileData
        :param old_state: The previous state of the tile, as a dictionary.
        :type old_state: dict
        :param new_state: The new state of the tile, as a dictionary.
        :type new_state: dict
        :param tile_item: The graphical item associated with the tile, if any.
        :type tile_item: QGraphicsItem or None
        """
        super().__init__(f"Edit Tile {tile_data.tile_id}")
        self.tile_data = tile_data
        self.old_state = old_state
        self.new_state = new_state
        self.tile_item = tile_item

    def undo(self):
        """
        Revert the tile to its previous state.
        """
        self._apply_state(self.old_state)

    def redo(self):
        """
        Apply the new state to the tile.
        """
        self._apply_state(self.new_state)

    def _apply_state(self, state):
        """
        Apply a given state to the tile.

        :param state: The state to apply to the tile.
        :type state: dict
        """
        from models.tiles.tile_data import TileData
        self.tile_data.terrain = TerrainType[state["terrain"]]
        self.tile_data.tags = [TileTag[t] for t in state["tags"]]
        self.tile_data.user_label = state["user_label"]
        self.tile_data.note = state["note"]
        self.tile_data.overlay_color = state["overlay_color"]
        self.tile_data.last_updated = state.get("last_updated")
        if self.tile_item:
            self.tile_item.set_overlay_color(self.tile_data.overlay_color)

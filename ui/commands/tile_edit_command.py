from PyQt5.QtWidgets import QUndoCommand
from copy import deepcopy

class TileEditCommand(QUndoCommand):
    """
    QUndoCommand for editing a tile's properties with undo/redo support.

    This command stores the original state of a tile and applies a new preset state,
    allowing changes to be undone and redone as needed.

    :param tile_data: The tile data object to be modified.
    :type tile_data: TileData
    :param new_state_preset: The preset containing the new state to apply to the tile.
    :type new_state_preset: TilePreset
    :param logic: The logic context required for applying the preset.
    :type logic: object
    :param description: Description for the undo command (default is "Edit Tile").
    :type description: str, optional

    :ivar tile_data: The tile data object being edited.
    :vartype tile_data: TileData
    :ivar old_state: A deep copy of the original tile state for undo operations.
    :vartype old_state: dict
    :ivar preset: The preset to apply to the tile.
    :vartype preset: TilePreset
    :ivar logic: The logic context for preset application.
    :vartype logic: object
    """

    def __init__(self, tile_data, new_state_preset, logic, description="Edit Tile"):
        """
        Initialize the TileEditCommand.

        :param tile_data: The tile data object to be modified.
        :type tile_data: TileData
        :param new_state_preset: The preset containing the new state to apply to the tile.
        :type new_state_preset: TilePreset
        :param logic: The logic context required for applying the preset.
        :type logic: object
        :param description: Description for the undo command (default is "Edit Tile").
        :type description: str, optional
        """
        super().__init__(description)
        # Deep‐copy the *original* TileData so we can restore it
        self.tile_data = tile_data
        self.old_state = {
            "terrain": tile_data.terrain,
            "tags": tile_data.tags.copy(),
            "overlay_color": tile_data.overlay_color,
            "note": tile_data.note,
            "user_label": tile_data.user_label,
            "entities": deepcopy(tile_data.entities),
            "triggers": deepcopy(tile_data.triggers),
        }
        self.preset = new_state_preset
        self.logic = logic

    def redo(self):
        """
        Apply the new preset to the tile.

        This method is called when the command is executed or redone.
        """
        self.preset.apply_to(self.tile_data, logic=self.logic)

    def undo(self):
        """
        Restore the tile to its previous state.

        This method is called when the command is undone.
        """
        td = self.tile_data
        td.terrain       = self.old_state["terrain"]
        td.tags          = self.old_state["tags"].copy()
        td.overlay_color = self.old_state["overlay_color"]
        td.note          = self.old_state["note"]
        td.user_label    = self.old_state["user_label"]
        td.entities      = deepcopy(self.old_state["entities"])
        td.triggers      = deepcopy(self.old_state["triggers"])
        # (Re‐subscribe triggers if needed—EventBus.subscribe was done on redo)

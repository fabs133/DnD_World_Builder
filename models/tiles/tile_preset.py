from copy import deepcopy
from models.tiles.tile_data import TerrainType, TileTag, TileData
from core.gameCreation.trigger import Trigger
from models.entities.game_entity import GameEntity

class TilePreset:
    """
    Represents a preset configuration for a tile, including terrain, tags, overlay color,
    notes, user labels, entities, and triggers.

    :ivar terrain: The terrain type or object associated with the tile.
    :ivar tags: A list of tags associated with the tile.
    :ivar overlay_color: The overlay color for the tile.
    :ivar note: An optional note attached to the tile.
    :ivar user_label: An optional user-defined label for the tile.
    :ivar entities: A list of entities present on the tile.
    :ivar triggers: A list of triggers associated with the tile.
    """

    def __init__(self, terrain=None, tags=None, overlay_color=None,
                 note=None, user_label=None, entities=None, triggers=None):
        """
        Initialize a TilePreset instance.

        :param terrain: The terrain type or object for the tile (default is None).
        :param tags: Tags associated with the tile (default is None, which becomes an empty list).
        :param overlay_color: The overlay color for the tile (default is None).
        :param note: An optional note for the tile (default is None).
        :param user_label: An optional user label for the tile (default is None).
        :param entities: Entities present on the tile (default is None, which becomes an empty list).
        :param triggers: Triggers associated with the tile (default is None, which becomes an empty list).
        """
        self.terrain = terrain
        self.tags = tags or []
        self.overlay_color = overlay_color
        self.note = note
        self.user_label = user_label
        self.entities = deepcopy(entities) if entities else []
        self.triggers = deepcopy(triggers) if triggers else []

    @classmethod
    def from_tile_data(cls, tile_data: TileData):
        """
        Create a TilePreset instance from a TileData object.

        :param tile_data: The TileData object to copy data from.
        :type tile_data: TileData
        :return: A new TilePreset instance with data copied from the given TileData.
        :rtype: TilePreset
        """
        return cls(
            terrain=tile_data.terrain,
            tags=tile_data.tags.copy(),
            overlay_color=tile_data.overlay_color,
            note=tile_data.note,
            user_label=tile_data.user_label,
            entities=deepcopy(tile_data.entities),
            triggers=deepcopy(tile_data.triggers)
        )

    def apply_to(self, tile_data, logic=True):
        """
        Apply the preset's properties to a TileData object.

        :param tile_data: The TileData object to apply the preset to.
        :type tile_data: TileData
        :param logic: If True, also applies note, user_label, entities, and triggers (default is True).
        :type logic: bool, optional
        """
        tile_data.terrain = self.terrain
        tile_data.tags = self.tags.copy()
        tile_data.overlay_color = self.overlay_color

        if logic:
            tile_data.note = self.note
            tile_data.user_label = self.user_label
            tile_data.entities = deepcopy(self.entities)
            tile_data.triggers = deepcopy(self.triggers)

            from core.gameCreation.event_bus import EventBus
            for trig in tile_data.triggers:
                EventBus.subscribe(trig.event_type, trig.check_and_react)

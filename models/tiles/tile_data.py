from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from enum import Enum
from models.entities.game_entity import GameEntity  # Ensure this has to_dict/from_dict implemented
from core.gameCreation.trigger import Trigger  # Ensure this has to_dict/from_dict implemented

class TerrainType(Enum):
    """
    Enum for different types of terrain a tile can have.

    Attributes
    ----------
    GRASS : str
        Grass terrain.
    WATER : str
        Water terrain.
    MOUNTAIN : str
        Mountain terrain.
    FLOOR : str
        Floor terrain.
    WALL : str
        Wall terrain.
    CUSTOM : str
        Custom terrain.
    """
    GRASS = "grass"
    WATER = "water"
    MOUNTAIN = "mountain"
    FLOOR = "floor"
    WALL = "wall"
    CUSTOM = "custom"

class TileTag(Enum):
    """
    Enum for different tags that can be associated with a tile.

    Attributes
    ----------
    BLOCKS_MOVEMENT : str
        Tile blocks movement.
    BLOCKS_VISION : str
        Tile blocks vision.
    START_ZONE : str
        Tile is a start zone.
    TRAP_ZONE : str
        Tile is a trap zone.
    """
    BLOCKS_MOVEMENT = "blocks_movement"
    BLOCKS_VISION = "blocks_vision"
    START_ZONE = "start_zone"
    TRAP_ZONE = "trap_zone"

@dataclass
class TileData:
    """
    Dataclass for representing tile information in the DnDProject.

    Attributes
    ----------
    tile_id : str
        Unique identifier for the tile.
    position : Tuple[int, int]
        The (x, y) coordinates of the tile.
    terrain : TerrainType
        The type of terrain for the tile.
    entities : List[GameEntity]
        List of entities currently on the tile.
    note : Optional[str]
        Optional note attached to the tile.
    user_label : Optional[str]
        Optional user-defined label for the tile.
    overlay_color : Optional[str]
        Optional color overlay for the tile.
    tags : List[TileTag]
        List of tags associated with the tile.
    last_updated : Optional[str]
        Timestamp of the last update to the tile.
    triggers : List[Trigger]
        List of triggers associated with the tile.
    """

    tile_id: str = "new_tile"
    position: Tuple[int, int] = (0, 0)
    terrain: TerrainType = TerrainType.FLOOR
    entities: List[GameEntity] = field(default_factory=list)
    note: Optional[str] = None
    user_label: Optional[str] = None
    overlay_color: Optional[str] = None
    tags: List[TileTag] = field(default_factory=list)
    last_updated: Optional[str] = None
    triggers: List[Trigger] = field(default_factory=list)
    background_image: Optional[str] = None
    ambient_audio: Optional[str] = None

    def is_occupied(self) -> bool:
        """
        Check if the tile is occupied by a player, NPC, or enemy entity.

        Returns
        -------
        bool
            True if the tile is occupied, False otherwise.
        """
        return any(e.entity_type in ["player", "npc", "enemy"] for e in self.entities)

    def has_entity_type(self, type_name: str) -> bool:
        """
        Check if the tile contains an entity of the specified type.

        Parameters
        ----------
        type_name : str
            The type name to check for.

        Returns
        -------
        bool
            True if an entity of the specified type is present, False otherwise.
        """
        return any(e.entity_type == type_name for e in self.entities)

    def add_entity(self, entity: GameEntity):
        """
        Add an entity to the tile.

        Parameters
        ----------
        entity : GameEntity
            The entity to add.
        """
        self.entities.append(entity)

    def remove_entity(self, entity: GameEntity):
        """
        Remove an entity from the tile if present.

        Parameters
        ----------
        entity : GameEntity
            The entity to remove.
        """
        if entity in self.entities:
            self.entities.remove(entity)
    
    def register_trigger(self, trigger):
        """
        Register a trigger to the tile and subscribe it to the EventBus.

        Parameters
        ----------
        trigger : Trigger
            The trigger to register.
        """
        from core.gameCreation.event_bus import EventBus  # if needed
        if trigger not in self.triggers:
            self.triggers.append(trigger)
            EventBus.subscribe(trigger.event_type, trigger.check_and_react)

    def to_dict(self) -> dict:
        """
        Serialize the TileData instance to a dictionary.

        Returns
        -------
        dict
            Dictionary representation of the TileData instance.
        """
        data = {
            "tile_id": self.tile_id,
            "triggers": [t.to_dict() for t in self.triggers],
            "position": self.position,
            "terrain": self.terrain.name,
            "tags": [tag.name for tag in self.tags],
            "user_label": self.user_label,
            "note": self.note,
            "overlay_color": self.overlay_color,
            "last_updated": self.last_updated,
            "entities": [e.to_dict() for e in self.entities],
        }
        if self.background_image:
            data["background_image"] = self.background_image
        if self.ambient_audio:
            data["ambient_audio"] = self.ambient_audio
        return data

    @classmethod
    def from_dict(cls, data):
        """
        Create a TileData instance from a dictionary, subscribing triggers to the EventBus.

        Parameters
        ----------
        data : dict
            Dictionary containing tile data.

        Returns
        -------
        TileData
            The created TileData instance.
        """
        triggers = [Trigger.from_dict(t) for t in data.get("triggers", [])]

        # Optional: auto-subscribe to EventBus after loading
        from core.gameCreation.event_bus import EventBus
        for trig in triggers:
            EventBus.subscribe(trig.event_type, trig.check_and_react)

        return cls(
            tile_id=data["tile_id"],
            position=tuple(data["position"]),
            terrain=TerrainType[data["terrain"]],
            tags=[TileTag[t] for t in data.get("tags", [])],
            user_label=data.get("user_label"),
            note=data.get("note"),
            overlay_color=data.get("overlay_color"),
            last_updated=data.get("last_updated"),
            entities=[GameEntity.from_dict(e) for e in data.get("entities", [])],
            triggers=triggers,
            background_image=data.get("background_image"),
            ambient_audio=data.get("ambient_audio"),
        )

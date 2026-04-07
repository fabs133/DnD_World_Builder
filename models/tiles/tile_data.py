from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from enum import Enum
from models.entities.game_entity import GameEntity  # Ensure this has to_dict/from_dict implemented
from core.gameCreation.trigger import Trigger  # Ensure this has to_dict/from_dict implemented
from models.tiles.tile_zone import TileZone

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
    SAND = "sand"
    SWAMP = "swamp"
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
    movement_cost: int = 5
    elevation: int = 0
    zones: List[TileZone] = field(default_factory=list)
    zone_id: Optional[str] = None
    # Optional override for the tile classifier. When set, bypasses the
    # heuristic and forces this tile into a specific prompt-builder path.
    # Valid values: "narrative" | "riddle" | "boss" | "pack" | "transit"
    tile_type: Optional[str] = None
    # Narrator-authored scene description used as a prompt anchor when
    # generating a background image for this tile.
    narrator_intro: Optional[str] = None
    # Large background landmarks anchored to this tile's LEFT or RIGHT edge.
    # Each entry is a dict:
    #   {"name": str, "description": str, "anchor": "left"|"right",
    #    "propagate": bool}  (propagate defaults to True)
    # Used by the prompt composer to create visual continuity with the
    # neighbouring tile on the opposite edge.
    edge_structures: List[dict] = field(default_factory=list)

    @property
    def has_zones(self) -> bool:
        """True if the tile has spatial sub-divisions."""
        return len(self.zones) > 0

    def get_zone(self) -> Optional[str]:
        """Return the encounter zone for this tile.

        Falls back to *user_label* when *zone_id* is not set.
        """
        return self.zone_id or self.user_label or None

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
        if self.movement_cost != 5:
            data["movement_cost"] = self.movement_cost
        if self.elevation != 0:
            data["elevation"] = self.elevation
        if self.zones:
            data["zones"] = [z.to_dict() for z in self.zones]
        if self.zone_id:
            data["zone_id"] = self.zone_id
        if self.tile_type:
            data["tile_type"] = self.tile_type
        if self.narrator_intro:
            data["narrator_intro"] = self.narrator_intro
        if self.edge_structures:
            data["edge_structures"] = list(self.edge_structures)
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
            movement_cost=data.get("movement_cost", 5),
            elevation=data.get("elevation", 0),
            zones=[TileZone.from_dict(z) for z in data.get("zones", [])],
            zone_id=data.get("zone_id"),
            tile_type=data.get("tile_type"),
            narrator_intro=data.get("narrator_intro"),
            edge_structures=list(data.get("edge_structures", [])),
        )

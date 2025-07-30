from enum import Enum

class EntityType(Enum):
    """
    Enumeration of possible entity types in the DnD project.

    :cvar PLAYER: Represents a player entity.
    :cvar ENEMY: Represents an enemy entity.
    :cvar NPC: Represents a non-player character entity.
    :cvar OBJECT: Represents an object entity.
    """
    PLAYER = "player"
    ENEMY = "enemy"
    NPC = "npc"
    OBJECT = "object"
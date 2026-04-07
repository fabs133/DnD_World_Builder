from enum import Enum


class EntityType(str, Enum):
    """
    Entity types in the DnD World Builder.

    Inherits from ``str`` for backward compatibility with existing
    string comparisons like ``entity_type == "player"``.
    """

    def __str__(self) -> str:
        return self.value

    PLAYER = "player"
    ENEMY = "enemy"
    NPC = "npc"
    MONSTER = "monster"
    HOSTILE = "hostile"
    ALLY = "ally"
    COMPANION = "companion"
    OBJECT = "object"
    ITEM = "item"
    TRAP = "trap"
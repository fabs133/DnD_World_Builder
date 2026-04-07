import pytest
from models.entities.entity_type import EntityType


def test_enum_members_exist():
    names = {e.name for e in EntityType}
    assert names == {
        "PLAYER", "ENEMY", "NPC", "MONSTER", "HOSTILE",
        "ALLY", "COMPANION", "OBJECT", "ITEM", "TRAP",
    }


def test_enum_values():
    assert EntityType.PLAYER.value == "player"
    assert EntityType.ENEMY.value == "enemy"
    assert EntityType.NPC.value == "npc"
    assert EntityType.MONSTER.value == "monster"
    assert EntityType.HOSTILE.value == "hostile"
    assert EntityType.ALLY.value == "ally"
    assert EntityType.COMPANION.value == "companion"
    assert EntityType.OBJECT.value == "object"
    assert EntityType.ITEM.value == "item"
    assert EntityType.TRAP.value == "trap"


def test_string_equality():
    """EntityType(str, Enum) compares equal to plain strings."""
    assert EntityType.PLAYER == "player"
    assert EntityType.ENEMY == "enemy"
    assert "npc" == EntityType.NPC


def test_membership_in_string_set():
    """EntityType values can be found in frozensets of strings."""
    s = frozenset({"player", "enemy"})
    assert EntityType.PLAYER in s
    assert EntityType.NPC not in s


def test_membership_in_enum_set():
    """Plain strings can be found in frozensets of EntityType."""
    s = frozenset({EntityType.PLAYER, EntityType.ENEMY})
    assert "player" in s
    assert "npc" not in s


def test_construction_from_string():
    assert EntityType("player") is EntityType.PLAYER
    assert EntityType("monster") is EntityType.MONSTER

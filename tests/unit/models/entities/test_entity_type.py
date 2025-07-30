import pytest
from models.entities.entity_type import EntityType

def test_enum_members_exist():
    # Check that all expected members are present
    names = {e.name for e in EntityType}
    assert names == {"PLAYER", "ENEMY", "NPC", "OBJECT"}

def test_enum_values():
    # Check that values match the spec
    assert EntityType.PLAYER.value == "player"
    assert EntityType.ENEMY.value  == "enemy"
    assert EntityType.NPC.value    == "npc"
    assert EntityType.OBJECT.value == "object"

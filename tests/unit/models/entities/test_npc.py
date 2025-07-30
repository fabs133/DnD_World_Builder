import pytest

from models.entities.npc import NPC
from models.entities.game_entity import GameEntity

@pytest.mark.parametrize("behavior", ["friendly", "neutral", "hostile", "confused"])
def test_npc_initialization_and_inheritance(behavior):
    npc = NPC("Bob", behavior)
    # Inherits GameEntity
    assert isinstance(npc, GameEntity)
    # Basic fields
    assert npc.name == "Bob"
    assert npc.entity_type == "npc"
    assert npc.stats == {}
    assert npc.inventory == []
    assert npc.triggers == []
    # Behavior stored verbatim
    assert npc.behavior == behavior

def test_take_turn_no_side_effects_or_errors():
    npc = NPC("Alice", "friendly")
    # Should simply return None and not raise
    assert npc.take_turn() is None

    # Try other behaviors
    for b in ["neutral", "hostile", "sneaky"]:
        npc.behavior = b
        assert npc.take_turn() is None

import pytest

from models.entities.trap import Trap
from models.entities.game_entity import GameEntity

def test_trap_initialization_and_inheritance():
    trap = Trap(name="Spike Pit", damage=10, trigger_range=2)
    # Inherits from GameEntity
    assert isinstance(trap, GameEntity)
    # Core attributes
    assert trap.name == "Spike Pit"
    assert trap.entity_type == "trap"
    assert trap.stats == {}
    assert trap.inventory == []
    assert trap.triggers == []
    # Trap‐specific attributes
    assert trap.damage == 10
    assert trap.trigger_range == 2

def test_take_turn_no_side_effects():
    trap = Trap("Snare", damage=5, trigger_range=1)
    # Should simply return None and not raise
    assert trap.take_turn() is None

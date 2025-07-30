import pytest

from models.flow.reaction.reactions_list import ApplyDamage, AlertGamemaster
from registries.reaction_registry import (
    ReactionRegistry, reaction_registry
)

def test_manual_register_and_get_class():
    reg = ReactionRegistry()
    # Initially empty
    assert reg.get_all() == []
    assert reg.get_class("X") is None

    # Register a dummy class
    class Dummy:
        @classmethod
        def from_dict(cls, data):
            return "dummy"
    reg.register("Dummy", Dummy)
    assert "Dummy" in reg.get_all()
    assert reg.get_class("Dummy") is Dummy

def test_create_known_types():
    # ApplyDamage
    data_ad = {"type": "ApplyDamage", "damage_type": "fire", "amount": 5}
    ad = reaction_registry.create(data_ad)
    assert isinstance(ad, ApplyDamage)
    # AlertGamemaster
    data_ag = {"type": "AlertGamemaster", "message": "Hi GM"}
    ag = reaction_registry.create(data_ag)
    assert isinstance(ag, AlertGamemaster)
    assert ag.message == "Hi GM"

def test_create_unknown_raises():
    bad = {"type": "NoSuch"}
    with pytest.raises(ValueError) as ei:
        reaction_registry.create(bad)
    msg = str(ei.value)
    assert "Unknown type: NoSuch" in msg

def test_list_and_get_all_are_equivalent():
    keys = reaction_registry.get_all()
    assert isinstance(keys, list)
    # Our two registered types
    assert "ApplyDamage" in keys
    assert "AlertGamemaster" in keys
    # list_keys alias
    assert set(reaction_registry.list_keys()) == set(keys)

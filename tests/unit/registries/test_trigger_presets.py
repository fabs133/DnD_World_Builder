import pytest

from core.gameCreation.trigger import Trigger
from models.flow.reaction.reactions_list import ApplyDamage, AlertGamemaster
from models.flow.condition.condition_list import AlwaysTrue, PerceptionCheck
from models.flow.reaction.reactions_list import ApplyDamage as apply_damage
from models.flow.condition.condition_list import AlwaysTrue as always_true
from models.flow.condition.condition_list import PerceptionCheck as perception_check
from models.flow.reaction.reactions_list import AlertGamemaster as alert_gamemaster

import registries.trigger_presets as tp_mod

def test_trigger_presets_keys():
    expected = {"player", "npc", "enemy", "trap", "object"}
    assert set(tp_mod.trigger_presets.keys()) == expected

def test_npc_trigger():
    lst = tp_mod.trigger_presets["npc"]
    assert len(lst) == 1
    trig = lst[0]
    assert isinstance(trig, Trigger)
    assert trig.event_type == "TALKED_TO"
    # condition is the AlwaysTrue class
    assert trig.condition is AlwaysTrue
    # reaction is an AlertGamemaster instance
    # reaction is the AlertGamemaster class (not an instance)
    assert trig.reaction is alert_gamemaster
    # You could instantiate it on the fly if you need to check its behavior:
    inst = trig.reaction.from_dict({"message": "hello"})
    assert isinstance(inst, AlertGamemaster)
    assert inst.message == "hello"

def test_enemy_trigger():
    lst = tp_mod.trigger_presets["enemy"]
    assert len(lst) == 1
    trig = lst[0]
    assert isinstance(trig, Trigger)
    assert trig.event_type == "PLAYER_IN_RANGE"
    # condition here was given as the integer 10
    assert trig.condition == 10
    # reaction is ApplyDamage("slashing", 1)
    assert isinstance(trig.reaction, ApplyDamage)
    assert (trig.reaction.damage_type, trig.reaction.amount) == ("slashing", 1)

def test_trap_trigger():
    lst = tp_mod.trigger_presets["trap"]
    assert len(lst) == 1
    trig = lst[0]
    assert isinstance(trig, Trigger)
    assert trig.event_type == "STEPPED_ON"
    # condition is a PerceptionCheck instance with dc 12
    assert isinstance(trig.condition, PerceptionCheck)
    assert trig.condition.dc == 12
    # reaction is ApplyDamage("piercing", 6)
    assert isinstance(trig.reaction, ApplyDamage)
    assert (trig.reaction.damage_type, trig.reaction.amount) == ("piercing", 6)

def test_empty_presets():
    assert tp_mod.trigger_presets["player"] == []
    assert tp_mod.trigger_presets["object"] == []

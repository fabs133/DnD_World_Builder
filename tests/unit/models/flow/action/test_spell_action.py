import pytest

import models.flow.action.spell_action as sa_mod
from models.flow.action.spell_action import SpellAction

class DummySpell:
    def __init__(self, dmg=None, heal=None, eff=None):
        # damage/healing should be dicts or None
        self.damage = dmg
        self.healing = heal
        self.effect = eff

class DummyTarget:
    def __init__(self):
        self.damage_taken = []
        self.heal_amounts = []
    def take_damage(self, amount, dmg_type):
        self.damage_taken.append((amount, dmg_type))
    def heal(self, amount):
        self.heal_amounts.append(amount)

@pytest.fixture(autouse=True)
def stub_roll_and_effect(monkeypatch):
    # stubbed roll: always returns 5
    monkeypatch.setattr(sa_mod, "roll", lambda expr: 5)
    # capture apply_effect calls
    calls = []
    monkeypatch.setattr(sa_mod, "apply_effect",
                        lambda tgt, eff: calls.append((tgt, eff)))
    return calls

def test_execute_damage_only(stub_roll_and_effect):
    spell = DummySpell(
        dmg={"amount":"1d1+0", "type":"fire"},
        heal=None,
        eff=None
    )
    tgt = DummyTarget()
    action = SpellAction(caster=None, spell=spell, targets=[tgt])

    action.execute(game_state=None)

    # roll was called => 5 damage
    assert tgt.damage_taken == [(5, "fire")]
    assert tgt.heal_amounts == []
    assert stub_roll_and_effect == []

def test_execute_healing_only(stub_roll_and_effect):
    spell = DummySpell(
        dmg=None,
        heal={"amount":"2d1+0"},
        eff=None
    )
    tgt = DummyTarget()
    action = SpellAction(caster=None, spell=spell, targets=[tgt])

    action.execute(game_state={})

    # heal branch only
    assert tgt.heal_amounts == [5]
    assert tgt.damage_taken == []
    assert stub_roll_and_effect == []

def test_execute_effect_only(stub_roll_and_effect):
    eff = {"type":"buff", "details":"haste", "duration":3}
    spell = DummySpell(dmg=None, heal=None, eff=eff)
    tgt = DummyTarget()
    action = SpellAction(caster=None, spell=spell, targets=[tgt])

    action.execute(game_state={})

    # effect branch only
    assert stub_roll_and_effect == [(tgt, eff)]
    assert tgt.damage_taken == []
    assert tgt.heal_amounts == []

def test_execute_all_branches(stub_roll_and_effect):
    spell = DummySpell(
        dmg={"amount":"1d1+0", "type":"cold"},
        heal={"amount":"1d1+0"},
        eff={"type":"slow", "details":"-2 speed", "duration":2}
    )
    tgt = DummyTarget()
    action = SpellAction(caster=None, spell=spell, targets=[tgt])

    action.execute(game_state={})

    # damage, heal, then effect
    assert tgt.damage_taken == [(5, "cold")]
    assert tgt.heal_amounts == [5]
    assert stub_roll_and_effect == [(tgt, spell.effect)]

def test_validate_not_implemented():
    # currently validate() is just `pass` → returns None which is falsy
    action = SpellAction(caster=None, spell=DummySpell(), targets=[])
    assert action.validate({}) is None
    # treat None as False in callers
    assert not action.validate(None)

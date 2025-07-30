import pytest

# Import from wherever your Spell class actually lives
from models.spell import Spell
import models.spell as spell_mod

class DummyTarget:
    def __init__(self):
        self.damage_taken = 0
        self.healed = 0
        self.effects = []

    def take_damage(self, amount):
        self.damage_taken += amount

    def heal(self, amount):
        self.healed += amount

@pytest.fixture(autouse=True)
def stub_roll_and_effect(monkeypatch):
    # stub roll to always return 7
    monkeypatch.setattr(spell_mod, "roll", lambda expr: 7)
    # capture apply_effect calls
    calls = []
    monkeypatch.setattr(spell_mod, "apply_effect",
                        lambda tgt, eff: calls.append((tgt, eff)))
    return calls

def test_calculate_damage_and_healing_and_effect(stub_roll_and_effect):
    dmg = {"amount": "1d1+0", "type": "fire"}
    heal = {"amount": "2d1+0"}
    eff = {"type": "buff", "details": "speed", "duration": 3}
    sp = Spell(
        name="Test",
        level=1,
        school="Evocation",
        casting_time="1 action",
        damage=dmg,
        healing=heal,
        effect=eff,
    )
    # calculate_damage uses stub roll
    assert sp.calculate_damage() == 7
    # calculate_healing uses stub roll
    assert sp.calculate_healing() == 7

    tgt = DummyTarget()
    # apply_effect should call the stub
    sp.apply_effect(tgt)
    assert stub_roll_and_effect == [(tgt, eff)]

def test_cast_combines_all_branches(stub_roll_and_effect):
    dmg = {"amount": "1d1+0"}
    heal = {"amount": "1d1+0"}
    eff = {"type": "debuff", "details": "slow", "duration": 2}
    sp = Spell(
        name="Combo",
        level=2,
        school="Illusion",
        casting_time="1 action",
        damage=dmg,
        healing=heal,
        effect=eff,
    )
    tgt = DummyTarget()
    # stub roll returns 7
    sp.cast(caster=None, target=tgt)
    # target.take_damage was called with calculate_damage()
    assert tgt.damage_taken == 7
    # target.heal was called
    assert tgt.healed == 7
    # apply_effect was called
    assert stub_roll_and_effect == [(tgt, eff)]

def test_cast_no_branches_does_nothing():
    sp = Spell(
        name="Empty",
        level=0,
        school="None",
        casting_time="1 action"
    )
    tgt = DummyTarget()
    # no damage/heal/effect => nothing happens
    sp.cast(None, tgt)
    assert tgt.damage_taken == 0
    assert tgt.healed == 0

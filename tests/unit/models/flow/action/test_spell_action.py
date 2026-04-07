"""Tests for SpellAction — validate and execute with full D&D 5e rules."""

import pytest
import random

from models.flow.action.spell_action import SpellAction
from models.spell import Spell
from models.entities.game_entity import GameEntity
from core.events import ENTITY_DAMAGED, ENTITY_DIED, SPELL_CAST
from core.gameCreation.event_bus import EventBus


@pytest.fixture(autouse=True)
def reset_bus():
    EventBus.reset()
    yield
    EventBus.reset()


def _entity(name, entity_type="player", hp=20, spell_slots=2, spells=None):
    e = GameEntity(name=name, entity_type=entity_type,
                   stats={"hp": hp, "max_hp": hp, "spell_slots": spell_slots})
    if spells:
        e.spells = spells
    e.position = (5, 5)
    e.action_used = False
    return e


def _spell(name="Fireball", level=3, damage=None, healing=None, effect=None,
           spell_range="60 feet"):
    return Spell(
        name=name, level=level, school="Evocation", casting_time="1 action",
        range=spell_range, damage=damage, healing=healing, effect=effect,
    )


FIREBALL = _spell(damage={"type": "fire", "amount": "2d6"})
CURE_WOUNDS = _spell("Cure Wounds", level=1, healing={"amount": "1d8"},
                      spell_range="Touch")
FIRE_BOLT = _spell("Fire Bolt", level=0, damage={"type": "fire", "amount": "1d10"})


# ── Validate ────────────────────────────────────────────────────────


class TestValidate:

    def test_success(self):
        caster = _entity("Wizard", spells=[FIREBALL], spell_slots=2)
        target = _entity("Goblin", "enemy")
        action = SpellAction(caster, FIREBALL, [target])
        assert action.validate(None) is True

    def test_no_spell_slots(self):
        caster = _entity("Wizard", spells=[FIREBALL], spell_slots=0)
        target = _entity("Goblin", "enemy")
        action = SpellAction(caster, FIREBALL, [target])
        assert action.validate(None) is False
        assert "No spell slots" in action.execution_log[-1]

    def test_cantrip_no_slots_ok(self):
        caster = _entity("Wizard", spells=[FIRE_BOLT], spell_slots=0)
        target = _entity("Goblin", "enemy")
        action = SpellAction(caster, FIRE_BOLT, [target])
        assert action.validate(None) is True

    def test_spell_not_known(self):
        caster = _entity("Wizard", spells=[], spell_slots=2)
        target = _entity("Goblin", "enemy")
        action = SpellAction(caster, FIREBALL, [target])
        assert action.validate(None) is False
        assert "does not know" in action.execution_log[-1]

    def test_caster_dead(self):
        caster = _entity("Wizard", hp=0, spells=[FIREBALL], spell_slots=2)
        target = _entity("Goblin", "enemy")
        action = SpellAction(caster, FIREBALL, [target])
        assert action.validate(None) is False

    def test_no_targets(self):
        caster = _entity("Wizard", spells=[FIREBALL], spell_slots=2)
        action = SpellAction(caster, FIREBALL, [])
        assert action.validate(None) is False

    def test_dict_spell_slots(self):
        caster = _entity("Wizard", spells=[FIREBALL])
        caster.spell_slots = {3: 2, 4: 1}
        target = _entity("Goblin", "enemy")
        action = SpellAction(caster, FIREBALL, [target])
        assert action.validate(None) is True

    def test_dict_spell_slots_depleted(self):
        caster = _entity("Wizard", spells=[FIREBALL])
        caster.spell_slots = {3: 0, 4: 0}
        target = _entity("Goblin", "enemy")
        action = SpellAction(caster, FIREBALL, [target])
        assert action.validate(None) is False


# ── Execute ─────────────────────────────────────────────────────────


class TestExecute:

    def test_deals_damage(self):
        caster = _entity("Wizard", spells=[FIREBALL], spell_slots=2)
        target = _entity("Goblin", "enemy", hp=20)
        action = SpellAction(caster, FIREBALL, [target], rng=random.Random(42))
        action.execute(None)
        assert target.hp < 20

    def test_deducts_slot_int(self):
        caster = _entity("Wizard", spells=[FIREBALL], spell_slots=2)
        target = _entity("Goblin", "enemy")
        SpellAction(caster, FIREBALL, [target], rng=random.Random(42)).execute(None)
        assert caster.spell_slots == 1

    def test_cantrip_no_slot_deduction(self):
        caster = _entity("Wizard", spells=[FIRE_BOLT], spell_slots=2)
        target = _entity("Goblin", "enemy")
        SpellAction(caster, FIRE_BOLT, [target], rng=random.Random(42)).execute(None)
        assert caster.spell_slots == 2

    def test_healing(self):
        caster = _entity("Cleric", spells=[CURE_WOUNDS], spell_slots=2)
        target = _entity("Fighter", hp=10)
        target.max_hp = 20
        SpellAction(caster, CURE_WOUNDS, [target], rng=random.Random(42)).execute(None)
        assert target.hp > 10

    def test_healing_caps_at_max(self):
        caster = _entity("Cleric", spells=[CURE_WOUNDS], spell_slots=2)
        target = _entity("Fighter", hp=19)
        target.max_hp = 20
        SpellAction(caster, CURE_WOUNDS, [target], rng=random.Random(42)).execute(None)
        assert target.hp <= 20

    def test_emits_spell_cast(self):
        events = []
        EventBus.subscribe(SPELL_CAST, lambda data: events.append(data))
        caster = _entity("Wizard", spells=[FIREBALL], spell_slots=2)
        target = _entity("Goblin", "enemy")
        SpellAction(caster, FIREBALL, [target], rng=random.Random(42)).execute(None)
        assert len(events) == 1
        assert events[0]["spell"] == "Fireball"

    def test_emits_entity_damaged(self):
        events = []
        EventBus.subscribe(ENTITY_DAMAGED, lambda data: events.append(data))
        caster = _entity("Wizard", spells=[FIREBALL], spell_slots=2)
        target = _entity("Goblin", "enemy")
        SpellAction(caster, FIREBALL, [target], rng=random.Random(42)).execute(None)
        assert len(events) == 1
        assert events[0]["entity_name"] == "Goblin"

    def test_returns_dict(self):
        caster = _entity("Wizard", spells=[FIREBALL], spell_slots=2)
        target = _entity("Goblin", "enemy")
        result = SpellAction(caster, FIREBALL, [target], rng=random.Random(42)).execute(None)
        assert result["action"] == "spell"
        assert result["spell"] == "Fireball"

    def test_stores_max_slots_for_rest(self):
        caster = _entity("Wizard", spells=[FIREBALL], spell_slots=3)
        target = _entity("Goblin", "enemy")
        SpellAction(caster, FIREBALL, [target], rng=random.Random(42)).execute(None)
        assert caster._max_spell_slots == 3

    def test_target_dies(self):
        events = []
        EventBus.subscribe(ENTITY_DIED, lambda data: events.append(data))
        caster = _entity("Wizard", spells=[FIREBALL], spell_slots=2)
        target = _entity("Goblin", "enemy", hp=1)
        SpellAction(caster, FIREBALL, [target], rng=random.Random(42)).execute(None)
        assert target.hp == 0
        assert len(events) == 1

    def test_execution_log(self):
        caster = _entity("Wizard", spells=[FIREBALL], spell_slots=2)
        target = _entity("Goblin", "enemy")
        action = SpellAction(caster, FIREBALL, [target], rng=random.Random(42))
        action.execute(None)
        assert any("casts Fireball" in line for line in action.execution_log)

    def test_effect_applied(self):
        spell = _spell("Hold Person", level=2,
                        effect={"type": "Paralyzed", "details": "Cannot move", "duration": 3})
        caster = _entity("Wizard", spells=[spell], spell_slots=2)
        target = _entity("Goblin", "enemy")
        SpellAction(caster, spell, [target]).execute(None)
        assert hasattr(target, "active_effects")
        assert any(e["type"] == "Paralyzed" for e in target.active_effects)

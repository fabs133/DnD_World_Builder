"""Tests for domain.specs.entity — Entity condition and state specs."""

import pytest

from domain.specs.entity import (
    Condition,
    INCAPACITATING_CONDITIONS,
    ATTACK_DISADVANTAGE_CONDITIONS,
    HasCondition,
    IsIncapacitated,
    IsAlive,
    HasHP,
    HasSpellSlot,
    HasAbilityUse,
    IsEntityType,
    HasFaction,
    CanTakeAction,
    CanTakeBonusAction,
    CanTakeReaction,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

class FakeEntity:
    def __init__(self, **kwargs):
        self.hp = kwargs.get("hp", 10)
        self.max_hp = kwargs.get("max_hp", 10)
        self.conditions = kwargs.get("conditions", [])
        self.entity_type = kwargs.get("entity_type", "player")
        self.faction = kwargs.get("faction", "player")
        self.spell_slots = kwargs.get("spell_slots", {})
        self.ability_uses = kwargs.get("ability_uses", {})
        self.is_dead = kwargs.get("is_dead", False)
        if "action_used" in kwargs:
            self.action_used = kwargs["action_used"]
        if "bonus_action_used" in kwargs:
            self.bonus_action_used = kwargs["bonus_action_used"]
        if "reaction_used" in kwargs:
            self.reaction_used = kwargs["reaction_used"]


# ── Condition enum ───────────────────────────────────────────────────────────

class TestConditionEnum:
    def test_all_incapacitating_conditions_exist(self):
        for c in INCAPACITATING_CONDITIONS:
            assert isinstance(c, Condition)

    def test_incapacitating_set(self):
        assert Condition.PARALYZED in INCAPACITATING_CONDITIONS
        assert Condition.STUNNED in INCAPACITATING_CONDITIONS
        assert Condition.UNCONSCIOUS in INCAPACITATING_CONDITIONS

    def test_attack_disadvantage_set(self):
        assert Condition.BLINDED in ATTACK_DISADVANTAGE_CONDITIONS
        assert Condition.POISONED in ATTACK_DISADVANTAGE_CONDITIONS


# ── HasCondition ─────────────────────────────────────────────────────────────

class TestHasCondition:
    def test_entity_has_condition(self):
        entity = FakeEntity(conditions=[Condition.PRONE])
        spec = HasCondition(Condition.PRONE)
        assert spec.is_satisfied_by(entity).passed is True

    def test_entity_lacks_condition(self):
        entity = FakeEntity(conditions=[])
        spec = HasCondition(Condition.PRONE)
        assert spec.is_satisfied_by(entity).passed is False

    def test_string_condition_value_match(self):
        entity = FakeEntity(conditions=["prone"])
        spec = HasCondition("prone")
        assert spec.is_satisfied_by(entity).passed is True

    def test_dict_candidate(self):
        candidate = {"conditions": ["blinded"]}
        spec = HasCondition("blinded")
        assert spec.is_satisfied_by(candidate).passed is True

    def test_rule_id(self):
        spec = HasCondition(Condition.STUNNED)
        assert spec.rule_id == "has_condition_stunned"

    def test_to_dict_roundtrip(self):
        spec = HasCondition(Condition.GRAPPLED)
        d = spec.to_dict()
        restored = HasCondition.from_dict(d)
        assert restored.condition == Condition.GRAPPLED


# ── IsIncapacitated ──────────────────────────────────────────────────────────

class TestIsIncapacitated:
    @pytest.mark.parametrize("cond", [
        Condition.INCAPACITATED,
        Condition.PARALYZED,
        Condition.PETRIFIED,
        Condition.STUNNED,
        Condition.UNCONSCIOUS,
    ])
    def test_detects_incapacitating_conditions(self, cond):
        entity = FakeEntity(conditions=[cond])
        assert IsIncapacitated().is_satisfied_by(entity).passed is True

    def test_not_incapacitated(self):
        entity = FakeEntity(conditions=[Condition.PRONE])
        assert IsIncapacitated().is_satisfied_by(entity).passed is False

    def test_no_conditions(self):
        entity = FakeEntity(conditions=[])
        assert IsIncapacitated().is_satisfied_by(entity).passed is False

    def test_string_condition_match(self):
        entity = FakeEntity(conditions=["stunned"])
        assert IsIncapacitated().is_satisfied_by(entity).passed is True


# ── IsAlive ──────────────────────────────────────────────────────────────────

class TestIsAlive:
    def test_alive_with_hp(self):
        entity = FakeEntity(hp=10)
        assert IsAlive().is_satisfied_by(entity).passed is True

    def test_dead_hp_zero(self):
        entity = FakeEntity(hp=0)
        assert IsAlive().is_satisfied_by(entity).passed is False

    def test_dead_flag(self):
        entity = FakeEntity(hp=0, is_dead=True)
        result = IsAlive().is_satisfied_by(entity)
        assert result.passed is False
        assert "dead" in result.message.lower()

    def test_dict_candidate(self):
        candidate = {"hp": 5}
        assert IsAlive().is_satisfied_by(candidate).passed is True


# ── HasHP ────────────────────────────────────────────────────────────────────

class TestHasHP:
    def test_meets_minimum(self):
        entity = FakeEntity(hp=10, max_hp=20)
        assert HasHP(minimum=10).is_satisfied_by(entity).passed is True

    def test_below_minimum(self):
        entity = FakeEntity(hp=5, max_hp=20)
        result = HasHP(minimum=10).is_satisfied_by(entity)
        assert result.passed is False
        assert result.data["deficit"] == 5

    def test_default_minimum_1(self):
        entity = FakeEntity(hp=1)
        assert HasHP().is_satisfied_by(entity).passed is True

    def test_zero_hp_fails_default(self):
        entity = FakeEntity(hp=0)
        assert HasHP().is_satisfied_by(entity).passed is False


# ── HasSpellSlot ─────────────────────────────────────────────────────────────

class TestHasSpellSlot:
    def test_has_slot(self):
        entity = FakeEntity(spell_slots={1: 3, 2: 1})
        assert HasSpellSlot(level=1).is_satisfied_by(entity).passed is True

    def test_no_slot(self):
        entity = FakeEntity(spell_slots={1: 0})
        assert HasSpellSlot(level=1).is_satisfied_by(entity).passed is False

    def test_missing_level(self):
        entity = FakeEntity(spell_slots={1: 2})
        assert HasSpellSlot(level=3).is_satisfied_by(entity).passed is False

    def test_invalid_level_raises(self):
        with pytest.raises(ValueError):
            HasSpellSlot(level=0)
        with pytest.raises(ValueError):
            HasSpellSlot(level=10)


# ── HasAbilityUse ────────────────────────────────────────────────────────────

class TestHasAbilityUse:
    def test_has_uses(self):
        entity = FakeEntity(ability_uses={"Second Wind": 1})
        assert HasAbilityUse("Second Wind").is_satisfied_by(entity).passed is True

    def test_no_uses(self):
        entity = FakeEntity(ability_uses={"Second Wind": 0})
        assert HasAbilityUse("Second Wind").is_satisfied_by(entity).passed is False

    def test_missing_ability(self):
        entity = FakeEntity(ability_uses={})
        assert HasAbilityUse("Action Surge").is_satisfied_by(entity).passed is False


# ── IsEntityType ─────────────────────────────────────────────────────────────

class TestIsEntityType:
    def test_matches(self):
        entity = FakeEntity(entity_type="player")
        assert IsEntityType("player").is_satisfied_by(entity).passed is True

    def test_no_match(self):
        entity = FakeEntity(entity_type="enemy")
        assert IsEntityType("player").is_satisfied_by(entity).passed is False

    def test_case_insensitive(self):
        entity = FakeEntity(entity_type="Player")
        assert IsEntityType("PLAYER").is_satisfied_by(entity).passed is True


# ── HasFaction ───────────────────────────────────────────────────────────────

class TestHasFaction:
    def test_matches(self):
        entity = FakeEntity(faction="rebels")
        assert HasFaction("rebels").is_satisfied_by(entity).passed is True

    def test_no_match(self):
        entity = FakeEntity(faction="empire")
        assert HasFaction("rebels").is_satisfied_by(entity).passed is False

    def test_case_insensitive(self):
        entity = FakeEntity(faction="Rebels")
        assert HasFaction("REBELS").is_satisfied_by(entity).passed is True


# ── CanTakeAction ────────────────────────────────────────────────────────────

class TestCanTakeAction:
    def test_can_act(self):
        entity = FakeEntity()
        assert CanTakeAction().is_satisfied_by(entity).passed is True

    def test_incapacitated_cannot_act(self):
        entity = FakeEntity(conditions=[Condition.STUNNED])
        result = CanTakeAction().is_satisfied_by(entity)
        assert result.passed is False

    def test_action_already_used(self):
        entity = FakeEntity(action_used=True)
        result = CanTakeAction().is_satisfied_by(entity)
        assert result.passed is False

    def test_action_used_via_context(self):
        entity = FakeEntity()
        result = CanTakeAction().is_satisfied_by(entity, {"action_used": True})
        assert result.passed is False


# ── CanTakeBonusAction ───────────────────────────────────────────────────────

class TestCanTakeBonusAction:
    def test_can_take(self):
        entity = FakeEntity()
        assert CanTakeBonusAction().is_satisfied_by(entity).passed is True

    def test_incapacitated_blocks(self):
        entity = FakeEntity(conditions=[Condition.PARALYZED])
        assert CanTakeBonusAction().is_satisfied_by(entity).passed is False

    def test_already_used(self):
        entity = FakeEntity(bonus_action_used=True)
        assert CanTakeBonusAction().is_satisfied_by(entity).passed is False


# ── CanTakeReaction ──────────────────────────────────────────────────────────

class TestCanTakeReaction:
    def test_can_react(self):
        entity = FakeEntity()
        assert CanTakeReaction().is_satisfied_by(entity).passed is True

    def test_incapacitated_blocks(self):
        entity = FakeEntity(conditions=[Condition.UNCONSCIOUS])
        assert CanTakeReaction().is_satisfied_by(entity).passed is False

    def test_already_used(self):
        entity = FakeEntity(reaction_used=True)
        assert CanTakeReaction().is_satisfied_by(entity).passed is False

    def test_used_via_context(self):
        entity = FakeEntity()
        assert CanTakeReaction().is_satisfied_by(entity, {"reaction_used": True}).passed is False

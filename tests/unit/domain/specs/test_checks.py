"""Tests for domain.specs.checks — Skill checks, saving throws, contests."""

import pytest

from domain.specs.checks import (
    DiceRollType,
    RollContext,
    SkillCheckSpec,
    SavingThrowSpec,
    ContestSpec,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

class FakeEntity:
    """Minimal entity for testing skill checks."""

    def __init__(self, skill_modifiers=None, stats=None, save_modifiers=None):
        if skill_modifiers is not None:
            self.skill_modifiers = skill_modifiers
        if stats is not None:
            self.stats = stats
        if save_modifiers is not None:
            self.save_modifiers = save_modifiers


# ── RollContext ──────────────────────────────────────────────────────────────

class TestRollContext:
    def test_natural_roll_defaults_to_roll(self):
        rc = RollContext(roll=15)
        assert rc.natural_roll == 15

    def test_explicit_natural_roll(self):
        rc = RollContext(roll=15, natural_roll=20)
        assert rc.natural_roll == 20

    def test_to_dict_roundtrip(self):
        original = RollContext(roll=12, natural_roll=12, roll_type=DiceRollType.ADVANTAGE, rolls=(12, 8))
        d = original.to_dict()
        restored = RollContext.from_dict(d)
        assert restored.roll == 12
        assert restored.roll_type == DiceRollType.ADVANTAGE
        assert restored.rolls == (12, 8)


# ── SkillCheckSpec ───────────────────────────────────────────────────────────

class TestSkillCheckSpec:
    def test_passes_when_total_meets_dc(self):
        spec = SkillCheckSpec("Perception", dc=15)
        entity = FakeEntity(skill_modifiers={"Perception": 5})
        result = spec.is_satisfied_by(entity, {"roll": 10})
        assert result.passed is True  # 10 + 5 = 15 >= 15

    def test_fails_when_total_below_dc(self):
        spec = SkillCheckSpec("Perception", dc=15)
        entity = FakeEntity(skill_modifiers={"Perception": 3})
        result = spec.is_satisfied_by(entity, {"roll": 8})
        assert result.passed is False  # 8 + 3 = 11 < 15

    def test_no_roll_returns_failure(self):
        spec = SkillCheckSpec("Stealth", dc=10)
        result = spec.is_satisfied_by(FakeEntity(), {})
        assert result.passed is False
        assert "roll" in result.suggested_fix.lower()

    def test_no_context_returns_failure(self):
        spec = SkillCheckSpec("Stealth", dc=10)
        result = spec.is_satisfied_by(FakeEntity())
        assert result.passed is False

    def test_auto_pass_on_nat_20(self):
        spec = SkillCheckSpec("Athletics", dc=30, auto_pass_on_nat_20=True)
        entity = FakeEntity(skill_modifiers={"Athletics": 0})
        ctx = {"roll_context": RollContext(roll=20, natural_roll=20)}
        result = spec.is_satisfied_by(entity, ctx)
        assert result.passed is True

    def test_nat_20_no_auto_pass_by_default(self):
        spec = SkillCheckSpec("Athletics", dc=30)
        entity = FakeEntity(skill_modifiers={"Athletics": 0})
        result = spec.is_satisfied_by(entity, {"roll_context": RollContext(roll=20, natural_roll=20)})
        assert result.passed is False  # 20 + 0 = 20 < 30

    def test_auto_fail_on_nat_1(self):
        spec = SkillCheckSpec("Stealth", dc=5, auto_fail_on_nat_1=True)
        entity = FakeEntity(skill_modifiers={"Stealth": 10})
        ctx = {"roll_context": RollContext(roll=1, natural_roll=1)}
        result = spec.is_satisfied_by(entity, ctx)
        assert result.passed is False

    def test_modifier_from_stats_dict(self):
        spec = SkillCheckSpec("Perception", dc=12)
        entity = FakeEntity(stats={"Perception": 4})
        result = spec.is_satisfied_by(entity, {"roll": 10})
        assert result.passed is True  # 10 + 4 = 14 >= 12

    def test_modifier_from_dict_candidate(self):
        spec = SkillCheckSpec("Stealth", dc=10)
        candidate = {"skill_modifiers": {"Stealth": 3}}
        result = spec.is_satisfied_by(candidate, {"roll": 8})
        assert result.passed is True  # 8 + 3 = 11 >= 10

    def test_roll_context_from_dict_in_context(self):
        spec = SkillCheckSpec("Perception", dc=10)
        entity = FakeEntity(skill_modifiers={"Perception": 2})
        ctx = {"roll_context": {"roll": 10, "natural_roll": 10}}
        result = spec.is_satisfied_by(entity, ctx)
        assert result.passed is True

    def test_rule_id_format(self):
        spec = SkillCheckSpec("Perception", dc=15)
        assert spec.rule_id == "skill_check_perception_dc15"

    def test_to_dict_roundtrip(self):
        original = SkillCheckSpec("Perception", dc=15, auto_pass_on_nat_20=True)
        d = original.to_dict()
        restored = SkillCheckSpec.from_dict(d)
        assert restored.skill == "Perception"
        assert restored.dc == 15
        assert restored.auto_pass_on_nat_20 is True

    def test_result_data_contains_details(self):
        spec = SkillCheckSpec("Perception", dc=15)
        entity = FakeEntity(skill_modifiers={"Perception": 3})
        result = spec.is_satisfied_by(entity, {"roll": 10})
        assert result.data["skill"] == "Perception"
        assert result.data["dc"] == 15
        assert result.data["roll"] == 10
        assert result.data["modifier"] == 3
        assert result.data["total"] == 13

    def test_advantage_label_in_message(self):
        spec = SkillCheckSpec("Stealth", dc=10)
        entity = FakeEntity(skill_modifiers={"Stealth": 2})
        ctx = {"roll_context": RollContext(roll=15, roll_type=DiceRollType.ADVANTAGE)}
        result = spec.is_satisfied_by(entity, ctx)
        assert "[ADV]" in result.message


# ── SavingThrowSpec ──────────────────────────────────────────────────────────

class TestSavingThrowSpec:
    def test_passes_when_meeting_dc(self):
        spec = SavingThrowSpec("DEX", dc=14)
        entity = FakeEntity(save_modifiers={"DEX": 4})
        result = spec.is_satisfied_by(entity, {"roll": 10})
        assert result.passed is True  # 10 + 4 = 14

    def test_fails_when_below_dc(self):
        spec = SavingThrowSpec("WIS", dc=15)
        entity = FakeEntity(save_modifiers={"WIS": 2})
        result = spec.is_satisfied_by(entity, {"roll": 10})
        assert result.passed is False  # 10 + 2 = 12

    def test_invalid_ability_raises(self):
        with pytest.raises(ValueError, match="Invalid ability"):
            SavingThrowSpec("XYZ", dc=10)

    def test_case_insensitive_ability(self):
        spec = SavingThrowSpec("dex", dc=10)
        assert spec.ability == "DEX"

    def test_no_roll_returns_failure(self):
        spec = SavingThrowSpec("CON", dc=10)
        result = spec.is_satisfied_by(FakeEntity(), {})
        assert result.passed is False

    def test_death_save_nat_20(self):
        spec = SavingThrowSpec("CON", dc=10, is_death_save=True)
        result = spec.is_satisfied_by(FakeEntity(), {"roll": 20, "natural_roll": 20})
        assert result.passed is True
        assert "Natural 20" in result.message

    def test_death_save_nat_1(self):
        spec = SavingThrowSpec("CON", dc=10, is_death_save=True)
        result = spec.is_satisfied_by(FakeEntity(), {"roll": 1, "natural_roll": 1})
        assert result.passed is False
        assert result.data.get("failures") == 2

    def test_rule_id_for_death_save(self):
        spec = SavingThrowSpec("CON", dc=10, is_death_save=True)
        assert spec.rule_id.startswith("death_save")

    def test_rule_id_for_normal_save(self):
        spec = SavingThrowSpec("STR", dc=15)
        assert spec.rule_id == "save_str_dc15"

    def test_to_dict_roundtrip(self):
        original = SavingThrowSpec("CHA", dc=12, is_death_save=False)
        d = original.to_dict()
        restored = SavingThrowSpec.from_dict(d)
        assert restored.ability == "CHA"
        assert restored.dc == 12

    def test_save_modifier_from_stats(self):
        spec = SavingThrowSpec("DEX", dc=12)
        entity = FakeEntity(stats={"DEX_save": 5})
        result = spec.is_satisfied_by(entity, {"roll": 8})
        assert result.passed is True  # 8 + 5 = 13


# ── ContestSpec ──────────────────────────────────────────────────────────────

class TestContestSpec:
    def test_initiator_wins(self):
        spec = ContestSpec("Athletics", ["Athletics", "Acrobatics"])
        attacker = FakeEntity(skill_modifiers={"Athletics": 5})
        defender = FakeEntity(skill_modifiers={"Athletics": 2})
        ctx = {"initiator_roll": 12, "defender_roll": 10, "defender": defender}
        result = spec.is_satisfied_by(attacker, ctx)
        assert result.passed is True  # 17 vs 12

    def test_defender_wins(self):
        spec = ContestSpec("Athletics", ["Acrobatics"])
        attacker = FakeEntity(skill_modifiers={"Athletics": 1})
        defender = FakeEntity(skill_modifiers={"Acrobatics": 5})
        ctx = {"initiator_roll": 8, "defender_roll": 12, "defender": defender}
        result = spec.is_satisfied_by(attacker, ctx)
        assert result.passed is False  # 9 vs 17

    def test_tie_goes_to_initiator(self):
        spec = ContestSpec("Athletics", ["Athletics"])
        attacker = FakeEntity(skill_modifiers={"Athletics": 3})
        defender = FakeEntity(skill_modifiers={"Athletics": 3})
        ctx = {"initiator_roll": 10, "defender_roll": 10, "defender": defender}
        result = spec.is_satisfied_by(attacker, ctx)
        assert result.passed is True  # 13 vs 13, tie goes to initiator

    def test_missing_rolls(self):
        spec = ContestSpec("Athletics", ["Athletics"])
        result = spec.is_satisfied_by(FakeEntity(), {})
        assert result.passed is False

    def test_no_defender_in_context(self):
        spec = ContestSpec("Athletics", ["Athletics"])
        attacker = FakeEntity(skill_modifiers={"Athletics": 5})
        ctx = {"initiator_roll": 10, "defender_roll": 8}
        result = spec.is_satisfied_by(attacker, ctx)
        assert result.passed is True  # 15 vs 8 (no defender modifier)

    def test_rule_id(self):
        spec = ContestSpec("Athletics", ["Athletics", "Acrobatics"])
        assert "athletics" in spec.rule_id
        assert "vs" in spec.rule_id

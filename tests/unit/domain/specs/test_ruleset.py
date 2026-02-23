"""Tests for domain.specs.ruleset — Ruleset management."""

import json
import tempfile
from pathlib import Path

import pytest

from domain.specs.base import Specification, AlwaysTrue
from domain.specs.builder import RuleMask, RuleComponent, CompositionType
from domain.specs.registry import RuleCategory, RuleScope, get_default_registry
from domain.specs.ruleset import (
    RuleInstanceState,
    RuleInstance,
    CustomRule,
    Ruleset,
    RulesetManager,
    TriggerRuleBinding,
    create_default_ruleset,
    create_minimal_ruleset,
    create_dungeon_crawl_ruleset,
)


# ── RuleInstance ─────────────────────────────────────────────────────────────

class TestRuleInstance:
    def test_to_dict_roundtrip(self):
        inst = RuleInstance(
            rule_id="skill_check",
            params={"skill": "Perception", "dc": 15},
            inverted=True,
            state=RuleInstanceState.ENABLED,
            custom_name="Trap Check",
        )
        d = inst.to_dict()
        restored = RuleInstance.from_dict(d)
        assert restored.rule_id == "skill_check"
        assert restored.params["dc"] == 15
        assert restored.inverted is True
        assert restored.custom_name == "Trap Check"

    def test_create_spec(self):
        registry = get_default_registry()
        inst = RuleInstance(rule_id="is_alive", state=RuleInstanceState.ENABLED)
        spec = inst.create_spec(registry)
        assert spec is not None
        assert isinstance(spec, Specification)

    def test_create_spec_disabled_returns_none(self):
        registry = get_default_registry()
        inst = RuleInstance(rule_id="is_alive", state=RuleInstanceState.DISABLED)
        assert inst.create_spec(registry) is None

    def test_create_spec_unknown_rule_returns_none(self):
        registry = get_default_registry()
        inst = RuleInstance(rule_id="nonexistent")
        assert inst.create_spec(registry) is None

    def test_inverted_spec(self):
        registry = get_default_registry()
        inst = RuleInstance(rule_id="is_alive", inverted=True)
        spec = inst.create_spec(registry)
        # Inverted IsAlive → passes when dead
        entity = type("E", (), {"hp": 0, "is_dead": True})()
        assert spec.is_satisfied_by(entity).passed is True


# ── Ruleset ──────────────────────────────────────────────────────────────────

class TestRuleset:
    def test_add_rule(self):
        rs = Ruleset(ruleset_id="test", name="Test")
        inst = rs.add_rule("skill_check", skill="Stealth", dc=12)
        assert inst.rule_id == "skill_check"
        assert len(rs.active_rules) == 1

    def test_disable_enable_rule(self):
        rs = Ruleset(ruleset_id="test", name="Test")
        rs.add_rule("is_alive")
        rs.disable_rule("is_alive")
        assert rs.get_rule("is_alive").state == RuleInstanceState.DISABLED
        rs.enable_rule("is_alive")
        assert rs.get_rule("is_alive").state == RuleInstanceState.ENABLED

    def test_get_enabled_rules(self):
        rs = Ruleset(ruleset_id="test", name="Test")
        rs.add_rule("is_alive")
        rs.add_rule("can_take_action")
        rs.disable_rule("can_take_action")
        enabled = rs.get_enabled_rules()
        assert len(enabled) == 1
        assert enabled[0].rule_id == "is_alive"

    def test_add_custom_rule(self):
        rs = Ruleset(ruleset_id="test", name="Test")
        mask = RuleMask("m1", "Mask", "desc", [RuleComponent("is_alive", {})])
        custom = rs.add_custom_rule(mask)
        assert custom.instance_id.startswith("custom_")
        assert len(rs.custom_rules) == 1

    def test_build_all_specs(self):
        registry = get_default_registry()
        rs = Ruleset(ruleset_id="test", name="Test", enforce_base_rules=True)
        rs.add_rule("has_hp", minimum=1)
        specs = rs.build_all_specs(registry)
        assert len(specs) > 0

    def test_build_combined_spec(self):
        registry = get_default_registry()
        rs = Ruleset(ruleset_id="test", name="Test", enforce_base_rules=False)
        rs.add_rule("is_alive")
        combined = rs.build_combined_spec(registry)
        assert isinstance(combined, Specification)

    def test_empty_ruleset_combined_returns_always_true(self):
        registry = get_default_registry()
        rs = Ruleset(ruleset_id="test", name="Test", enforce_base_rules=False)
        combined = rs.build_combined_spec(registry)
        assert combined.is_satisfied_by(None).passed is True

    def test_to_dict_roundtrip(self):
        rs = Ruleset(ruleset_id="test", name="Test", description="A test")
        rs.add_rule("is_alive")
        d = rs.to_dict()
        restored = Ruleset.from_dict(d)
        assert restored.ruleset_id == "test"
        assert len(restored.active_rules) == 1

    def test_json_roundtrip(self):
        rs = Ruleset(ruleset_id="test", name="Test")
        rs.add_rule("is_alive")
        j = rs.to_json()
        restored = Ruleset.from_json(j)
        assert restored.name == "Test"

    def test_save_load(self, tmp_path):
        rs = Ruleset(ruleset_id="test", name="Test")
        rs.add_rule("is_alive")
        path = tmp_path / "test_ruleset.json"
        rs.save(path)
        loaded = Ruleset.load(path)
        assert loaded.ruleset_id == "test"
        assert len(loaded.active_rules) == 1


# ── Preset rulesets ──────────────────────────────────────────────────────────

class TestPresetRulesets:
    def test_default_ruleset(self):
        rs = create_default_ruleset()
        assert rs.ruleset_id == "default_5e"
        assert len(rs.active_rules) > 0

    def test_minimal_ruleset(self):
        rs = create_minimal_ruleset()
        assert rs.ruleset_id == "minimal"
        assert len(rs.active_rules) == 0
        assert rs.enforce_base_rules is True

    def test_dungeon_crawl_ruleset(self):
        rs = create_dungeon_crawl_ruleset()
        assert rs.ruleset_id == "dungeon_crawl"
        assert len(rs.active_rules) > 0


# ── RulesetManager ───────────────────────────────────────────────────────────

class TestRulesetManager:
    def test_has_presets(self):
        mgr = RulesetManager()
        assert mgr.get("default_5e") is not None
        assert mgr.get("minimal") is not None
        assert mgr.get("dungeon_crawl") is not None

    def test_set_active(self):
        mgr = RulesetManager()
        mgr.set_active("default_5e")
        assert mgr.get_active().ruleset_id == "default_5e"

    def test_create_ruleset(self):
        mgr = RulesetManager()
        rs = mgr.create_ruleset("Custom Rules", "My custom rules")
        assert rs.name == "Custom Rules"
        assert mgr.get(rs.ruleset_id) is rs

    def test_create_from_copy(self):
        mgr = RulesetManager()
        rs = mgr.create_ruleset("Copy of Default", copy_from="default_5e")
        assert len(rs.active_rules) > 0

    def test_delete(self):
        mgr = RulesetManager()
        rs = mgr.create_ruleset("To Delete")
        mgr.delete(rs.ruleset_id)
        assert mgr.get(rs.ruleset_id) is None

    def test_delete_active_clears_active(self):
        mgr = RulesetManager()
        rs = mgr.create_ruleset("Active Then Delete")
        mgr.set_active(rs.ruleset_id)
        mgr.delete(rs.ruleset_id)
        assert mgr.get_active() is None

    def test_save_and_load(self, tmp_path):
        mgr = RulesetManager(storage_path=tmp_path)
        mgr.save_all()
        # Verify files were created
        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) >= 3  # At least the 3 presets


# ── TriggerRuleBinding ───────────────────────────────────────────────────────

class TestTriggerRuleBinding:
    def test_build_pre_specs(self):
        registry = get_default_registry()
        rs = Ruleset(ruleset_id="test", name="Test")
        rs.add_rule("is_alive")
        rs.add_rule("can_take_action")
        binding = TriggerRuleBinding(
            trigger_id="t1",
            ruleset=rs,
            pre_spec_rule_ids=["is_alive", "can_take_action"],
        )
        specs = binding.build_pre_specs(registry)
        assert len(specs) == 2

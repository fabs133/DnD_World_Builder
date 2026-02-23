"""Tests for domain.specs.registry — Rule registry and definitions."""

import pytest

from domain.specs.base import AlwaysTrue, Specification
from domain.specs.registry import (
    RuleCategory,
    RuleScope,
    RuleParameter,
    RuleDefinition,
    RuleRegistry,
    get_default_registry,
    register_custom_rule,
)


# ── RuleParameter ────────────────────────────────────────────────────────────

class TestRuleParameter:
    def test_to_dict_roundtrip(self):
        p = RuleParameter(
            name="dc",
            param_type="int",
            label="DC",
            description="Difficulty",
            default=10,
            min_value=1,
            max_value=30,
        )
        d = p.to_dict()
        restored = RuleParameter.from_dict(d)
        assert restored.name == "dc"
        assert restored.default == 10
        assert restored.min_value == 1


# ── RuleDefinition ───────────────────────────────────────────────────────────

class TestRuleDefinition:
    def test_create_spec(self):
        rule_def = RuleDefinition(
            rule_id="always_true",
            name="Always True",
            description="Always passes",
            category=RuleCategory.BASE,
            scope=RuleScope.ENTITY,
            spec_class=AlwaysTrue,
        )
        spec = rule_def.create_spec()
        assert spec.is_satisfied_by(None).passed is True

    def test_create_spec_with_params(self):
        from domain.specs.entity import HasHP
        rule_def = RuleDefinition(
            rule_id="has_hp",
            name="Has HP",
            description="Check HP",
            category=RuleCategory.RESOURCES,
            scope=RuleScope.ENTITY,
            spec_class=HasHP,
            parameters=[
                RuleParameter("minimum", "int", "Min HP", default=1),
            ],
        )
        spec = rule_def.create_spec(minimum=5)
        assert spec.minimum == 5

    def test_create_spec_uses_defaults(self):
        from domain.specs.entity import HasHP
        rule_def = RuleDefinition(
            rule_id="has_hp",
            name="Has HP",
            description="Check HP",
            category=RuleCategory.RESOURCES,
            scope=RuleScope.ENTITY,
            spec_class=HasHP,
            parameters=[
                RuleParameter("minimum", "int", "Min HP", default=1),
            ],
        )
        spec = rule_def.create_spec()
        assert spec.minimum == 1

    def test_validate_params_missing_required(self):
        rule_def = RuleDefinition(
            rule_id="test",
            name="Test",
            description="Test",
            category=RuleCategory.CUSTOM,
            scope=RuleScope.ENTITY,
            spec_class=AlwaysTrue,
            parameters=[
                RuleParameter("required_param", "int", "Required", required=True),
            ],
        )
        errors = rule_def.validate_params()
        assert len(errors) > 0

    def test_validate_params_range(self):
        rule_def = RuleDefinition(
            rule_id="test",
            name="Test",
            description="Test",
            category=RuleCategory.CUSTOM,
            scope=RuleScope.ENTITY,
            spec_class=AlwaysTrue,
            parameters=[
                RuleParameter("val", "int", "Value", min_value=1, max_value=10),
            ],
        )
        errors = rule_def.validate_params(val=15)
        assert any("at most" in e for e in errors)

    def test_to_dict(self):
        rule_def = RuleDefinition(
            rule_id="test",
            name="Test",
            description="A test",
            category=RuleCategory.COMBAT,
            scope=RuleScope.ENTITY,
            spec_class=AlwaysTrue,
            tags=["test"],
        )
        d = rule_def.to_dict()
        assert d["rule_id"] == "test"
        assert d["category"] == "combat"
        assert "test" in d["tags"]


# ── RuleRegistry ─────────────────────────────────────────────────────────────

class TestRuleRegistry:
    def test_register_and_get(self):
        registry = RuleRegistry()
        rule = RuleDefinition(
            rule_id="my_rule",
            name="My Rule",
            description="Test",
            category=RuleCategory.CUSTOM,
            scope=RuleScope.ENTITY,
            spec_class=AlwaysTrue,
        )
        registry.register(rule)
        assert registry.get("my_rule") is rule

    def test_unregister(self):
        registry = RuleRegistry()
        rule = RuleDefinition(
            rule_id="temp",
            name="Temp",
            description="Temp",
            category=RuleCategory.CUSTOM,
            scope=RuleScope.ENTITY,
            spec_class=AlwaysTrue,
        )
        registry.register(rule)
        registry.unregister("temp")
        assert registry.get("temp") is None

    def test_get_by_category(self):
        registry = RuleRegistry()
        registry.register(RuleDefinition("r1", "R1", "d", RuleCategory.COMBAT, RuleScope.ENTITY, AlwaysTrue))
        registry.register(RuleDefinition("r2", "R2", "d", RuleCategory.MOVEMENT, RuleScope.TILE, AlwaysTrue))
        combat = registry.get_by_category(RuleCategory.COMBAT)
        assert len(combat) == 1
        assert combat[0].rule_id == "r1"

    def test_get_base_rules(self):
        registry = RuleRegistry()
        registry.register(RuleDefinition("base", "Base", "d", RuleCategory.BASE, RuleScope.ENTITY, AlwaysTrue, is_base_rule=True))
        registry.register(RuleDefinition("opt", "Opt", "d", RuleCategory.OPTIONAL, RuleScope.ENTITY, AlwaysTrue, is_base_rule=False))
        base = registry.get_base_rules()
        assert len(base) == 1
        assert base[0].rule_id == "base"

    def test_search(self):
        registry = RuleRegistry()
        registry.register(RuleDefinition("perc", "Perception Check", "Check perception", RuleCategory.COMBAT, RuleScope.ENTITY, AlwaysTrue, tags=["skill"]))
        results = registry.search("perception")
        assert len(results) == 1

    def test_get_all(self):
        registry = RuleRegistry()
        registry.register(RuleDefinition("r1", "R1", "d", RuleCategory.CUSTOM, RuleScope.ENTITY, AlwaysTrue))
        assert len(registry.get_all()) == 1

    def test_register_defaults(self):
        registry = RuleRegistry()
        registry.register_defaults()
        assert len(registry.get_all()) > 0
        assert registry.get("is_alive") is not None
        assert registry.get("skill_check") is not None


# ── Global functions ─────────────────────────────────────────────────────────

class TestGlobalRegistry:
    def test_get_default_registry(self):
        registry = get_default_registry()
        assert registry.get("is_alive") is not None

    def test_register_custom_rule(self):
        rule = RuleDefinition("custom_test", "Custom", "d", RuleCategory.CUSTOM, RuleScope.ENTITY, AlwaysTrue)
        register_custom_rule(rule)
        assert get_default_registry().get("custom_test") is not None

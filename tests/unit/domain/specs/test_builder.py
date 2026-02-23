"""Tests for domain.specs.builder — Rule builder and mask templates."""

import json

import pytest

from domain.specs.base import Specification
from domain.specs.builder import (
    CompositionType,
    RuleComponent,
    RuleMask,
    RuleBuilder,
    MaskLibrary,
    trap_template,
    zone_effect_template,
    combat_prerequisite_template,
    get_default_library,
)
from domain.specs.registry import RuleCategory, RuleRegistry, get_default_registry


# ── RuleComponent ────────────────────────────────────────────────────────────

class TestRuleComponent:
    def test_to_dict_roundtrip(self):
        comp = RuleComponent(rule_id="skill_check", params={"skill": "Stealth", "dc": 12}, inverted=True)
        d = comp.to_dict()
        restored = RuleComponent.from_dict(d)
        assert restored.rule_id == "skill_check"
        assert restored.params["dc"] == 12
        assert restored.inverted is True


# ── RuleMask ─────────────────────────────────────────────────────────────────

class TestRuleMask:
    def test_instantiate_single_component(self):
        registry = get_default_registry()
        mask = RuleMask(
            mask_id="test",
            name="Test",
            description="Test mask",
            components=[RuleComponent("is_alive", {})],
        )
        spec = mask.instantiate(registry)
        assert isinstance(spec, Specification)

    def test_instantiate_and_compose(self):
        registry = get_default_registry()
        mask = RuleMask(
            mask_id="test",
            name="Test",
            description="Test",
            components=[
                RuleComponent("is_alive", {}),
                RuleComponent("is_incapacitated", {}, inverted=True),
            ],
            composition=CompositionType.AND,
        )
        spec = mask.instantiate(registry)
        assert isinstance(spec, Specification)

    def test_empty_mask_returns_always_true(self):
        registry = get_default_registry()
        mask = RuleMask(mask_id="empty", name="Empty", description="", components=[])
        spec = mask.instantiate(registry)
        assert spec.is_satisfied_by(None).passed is True

    def test_unknown_rule_raises(self):
        registry = RuleRegistry()
        mask = RuleMask(
            mask_id="bad",
            name="Bad",
            description="",
            components=[RuleComponent("nonexistent", {})],
        )
        with pytest.raises(ValueError, match="Unknown rule"):
            mask.instantiate(registry)

    def test_to_dict_roundtrip(self):
        mask = RuleMask(
            mask_id="m1",
            name="Mask 1",
            description="Test",
            components=[RuleComponent("is_alive", {})],
            composition=CompositionType.OR,
            category=RuleCategory.TRAPS,
            author="tester",
            version="2.0",
            tags=["test"],
        )
        d = mask.to_dict()
        restored = RuleMask.from_dict(d)
        assert restored.mask_id == "m1"
        assert restored.composition == CompositionType.OR
        assert restored.category == RuleCategory.TRAPS
        assert restored.author == "tester"

    def test_json_roundtrip(self):
        mask = RuleMask(
            mask_id="j1",
            name="JSON Test",
            description="",
            components=[RuleComponent("is_alive", {})],
        )
        j = mask.to_json()
        restored = RuleMask.from_json(j)
        assert restored.mask_id == "j1"


# ── RuleBuilder ──────────────────────────────────────────────────────────────

class TestRuleBuilder:
    def test_build_single_requirement(self):
        registry = get_default_registry()
        spec = RuleBuilder().require("is_alive").build(registry)
        assert isinstance(spec, Specification)

    def test_build_multiple_requirements(self):
        registry = get_default_registry()
        spec = (
            RuleBuilder()
            .require("is_alive")
            .require("is_incapacitated", inverted=True)
            .build(registry)
        )
        assert isinstance(spec, Specification)

    def test_convenience_methods(self):
        builder = RuleBuilder()
        builder.require_alive()
        builder.require_can_act()
        builder.require_has_movement(10)
        mask = builder.to_mask("test_mask")
        assert len(mask.components) == 3

    def test_require_not(self):
        builder = RuleBuilder()
        builder.require_not("is_incapacitated")
        mask = builder.to_mask()
        assert mask.components[0].inverted is True

    def test_clear(self):
        builder = RuleBuilder()
        builder.require("is_alive").require("can_take_action")
        builder.clear()
        mask = builder.to_mask()
        assert len(mask.components) == 0

    def test_named_and_described(self):
        builder = RuleBuilder().named("My Rule").described("Does stuff")
        mask = builder.to_mask()
        assert mask.name == "My Rule"
        assert mask.description == "Does stuff"

    def test_composition_modes(self):
        builder = RuleBuilder().combine_with_or()
        mask = builder.to_mask()
        assert mask.composition == CompositionType.OR


# ── Template factories ───────────────────────────────────────────────────────

class TestTemplates:
    def test_trap_template(self):
        mask = trap_template("Pit Trap", "Perception", dc=15)
        assert mask.category == RuleCategory.TRAPS
        assert len(mask.components) == 2
        assert mask.components[1].inverted is True  # Fires on failure

    def test_zone_effect_template(self):
        mask = zone_effect_template("Healing Zone", entity_types=["player", "npc"])
        assert mask.category == RuleCategory.ENVIRONMENTAL
        assert len(mask.components) == 2

    def test_zone_effect_no_filter(self):
        mask = zone_effect_template("Damage Zone")
        assert len(mask.components) == 0

    def test_combat_prerequisite_template(self):
        mask = combat_prerequisite_template("Melee Attack", requires_action=True, max_range=5)
        assert mask.category == RuleCategory.COMBAT
        # is_alive + NOT incapacitated + can_take_action + in_range
        assert len(mask.components) >= 3


# ── MaskLibrary ──────────────────────────────────────────────────────────────

class TestMaskLibrary:
    def test_has_defaults(self):
        lib = MaskLibrary()
        assert len(lib.get_all()) > 0

    def test_get_by_id(self):
        lib = MaskLibrary()
        mask = lib.get("trap_pit_trap")
        assert mask is not None

    def test_get_by_category(self):
        lib = MaskLibrary()
        traps = lib.get_by_category(RuleCategory.TRAPS)
        assert len(traps) > 0

    def test_search(self):
        lib = MaskLibrary()
        results = lib.search("trap")
        assert len(results) > 0

    def test_register_custom(self):
        lib = MaskLibrary()
        custom = RuleMask("custom1", "Custom", "desc", [])
        lib.register(custom)
        assert lib.get("custom1") is not None

    def test_get_default_library(self):
        lib = get_default_library()
        assert len(lib.get_all()) > 0

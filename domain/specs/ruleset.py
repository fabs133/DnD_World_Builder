"""
Ruleset - Active Rule Configuration for a Scenario

This module manages which rules are active for a given scenario/map.
It's the bridge between the rule registry and actual gameplay.

Key concepts:
- Ruleset: Configuration of active rules for a scenario
- RuleInstance: A configured rule with specific parameters
- RulesetManager: Handles saving/loading rulesets

A Ruleset is saved with each map/scenario, allowing different
maps to use different rule configurations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from enum import Enum
import json
from pathlib import Path

from domain.specs.base import Specification, AllOf, AnyOf
from domain.specs.registry import (
    RuleRegistry, RuleDefinition, RuleCategory, 
    get_default_registry
)
from domain.specs.builder import RuleMask, MaskLibrary, get_default_library


class RuleInstanceState(Enum):
    """State of a rule instance in a ruleset."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    INHERITED = "inherited"  # Use default from rule definition


@dataclass
class RuleInstance:
    """
    A specific configured instance of a rule.
    
    This represents a rule as used in a scenario, with:
    - Specific parameter values
    - Enabled/disabled state
    - Optional inversion
    
    Example:
        # A perception trap with DC 15
        instance = RuleInstance(
            rule_id="skill_check",
            params={"skill": "Perception", "dc": 15},
            inverted=True,  # Fires on failure
            state=RuleInstanceState.ENABLED,
        )
    """
    rule_id: str
    params: dict[str, Any] = field(default_factory=dict)
    inverted: bool = False
    state: RuleInstanceState = RuleInstanceState.ENABLED
    
    # Optional user customization
    custom_name: str | None = None
    custom_description: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "params": self.params,
            "inverted": self.inverted,
            "state": self.state.value,
            "custom_name": self.custom_name,
            "custom_description": self.custom_description,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuleInstance:
        return cls(
            rule_id=data["rule_id"],
            params=data.get("params", {}),
            inverted=data.get("inverted", False),
            state=RuleInstanceState(data.get("state", "enabled")),
            custom_name=data.get("custom_name"),
            custom_description=data.get("custom_description"),
        )
    
    def create_spec(self, registry: RuleRegistry) -> Specification | None:
        """
        Create the Specification for this instance.
        
        Returns None if disabled.
        """
        if self.state == RuleInstanceState.DISABLED:
            return None
        
        rule_def = registry.get(self.rule_id)
        if rule_def is None:
            return None
        
        spec = rule_def.create_spec(**self.params)
        
        if self.inverted:
            spec = ~spec
        
        return spec


@dataclass
class CustomRule:
    """
    A user-created custom rule stored in the ruleset.
    
    This wraps a RuleMask with instance-specific configuration.
    """
    instance_id: str  # Unique ID within this ruleset
    mask: RuleMask
    params: dict[str, Any] = field(default_factory=dict)
    state: RuleInstanceState = RuleInstanceState.ENABLED
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "mask": self.mask.to_dict(),
            "params": self.params,
            "state": self.state.value,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CustomRule:
        return cls(
            instance_id=data["instance_id"],
            mask=RuleMask.from_dict(data["mask"]),
            params=data.get("params", {}),
            state=RuleInstanceState(data.get("state", "enabled")),
        )
    
    def create_spec(self, registry: RuleRegistry) -> Specification | None:
        """Create the Specification for this custom rule."""
        if self.state == RuleInstanceState.DISABLED:
            return None
        
        return self.mask.instantiate(registry, **self.params)


@dataclass
class Ruleset:
    """
    Configuration of active rules for a scenario.
    
    This is saved with each map/scenario and determines
    which rules are in effect during gameplay.
    
    Structure:
    - base_rules: Core rules that are always active (from registry is_base_rule)
    - active_rules: Standard rules that are enabled
    - disabled_rules: Rules explicitly disabled
    - custom_rules: User-created custom rules
    - rule_overrides: Parameter overrides for standard rules
    """
    ruleset_id: str
    name: str
    description: str = ""
    
    # Rule configuration
    active_rules: list[RuleInstance] = field(default_factory=list)
    custom_rules: list[CustomRule] = field(default_factory=list)
    
    # Metadata
    version: str = "1.0"
    author: str = ""
    
    # Settings
    enforce_base_rules: bool = True  # Base rules cannot be disabled
    
    def add_rule(
        self, 
        rule_id: str, 
        inverted: bool = False,
        **params: Any
    ) -> RuleInstance:
        """Add a rule to the ruleset."""
        instance = RuleInstance(
            rule_id=rule_id,
            params=params,
            inverted=inverted,
            state=RuleInstanceState.ENABLED,
        )
        self.active_rules.append(instance)
        return instance
    
    def add_custom_rule(self, mask: RuleMask, **params: Any) -> CustomRule:
        """Add a custom rule from a mask."""
        import uuid
        
        custom = CustomRule(
            instance_id=f"custom_{uuid.uuid4().hex[:8]}",
            mask=mask,
            params=params,
            state=RuleInstanceState.ENABLED,
        )
        self.custom_rules.append(custom)
        return custom
    
    def disable_rule(self, rule_id: str):
        """Disable a rule by ID."""
        for instance in self.active_rules:
            if instance.rule_id == rule_id:
                instance.state = RuleInstanceState.DISABLED
                return
    
    def enable_rule(self, rule_id: str):
        """Enable a rule by ID."""
        for instance in self.active_rules:
            if instance.rule_id == rule_id:
                instance.state = RuleInstanceState.ENABLED
                return
    
    def get_rule(self, rule_id: str) -> RuleInstance | None:
        """Get a rule instance by ID."""
        for instance in self.active_rules:
            if instance.rule_id == rule_id:
                return instance
        return None
    
    def get_enabled_rules(self) -> list[RuleInstance]:
        """Get all enabled rule instances."""
        return [r for r in self.active_rules if r.state == RuleInstanceState.ENABLED]
    
    def get_enabled_custom_rules(self) -> list[CustomRule]:
        """Get all enabled custom rules."""
        return [r for r in self.custom_rules if r.state == RuleInstanceState.ENABLED]
    
    def build_all_specs(self, registry: RuleRegistry) -> list[Specification]:
        """
        Build Specifications for all enabled rules.
        
        Returns:
            List of all active specifications
        """
        specs = []
        
        # Add base rules if enforced
        if self.enforce_base_rules:
            for rule_def in registry.get_base_rules():
                specs.append(rule_def.create_spec())
        
        # Add active standard rules
        for instance in self.get_enabled_rules():
            spec = instance.create_spec(registry)
            if spec:
                specs.append(spec)
        
        # Add custom rules
        for custom in self.get_enabled_custom_rules():
            spec = custom.create_spec(registry)
            if spec:
                specs.append(spec)
        
        return specs
    
    def build_combined_spec(
        self, 
        registry: RuleRegistry,
        composition: str = "all"
    ) -> Specification:
        """
        Build a single combined Specification.
        
        Args:
            registry: Rule registry
            composition: "all" (AND) or "any" (OR)
        
        Returns:
            Combined specification
        """
        specs = self.build_all_specs(registry)
        
        if not specs:
            from domain.specs.base import AlwaysTrue
            return AlwaysTrue()
        
        if composition == "any":
            return AnyOf(*specs)
        else:
            return AllOf(*specs, short_circuit=True)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize ruleset for storage."""
        return {
            "ruleset_id": self.ruleset_id,
            "name": self.name,
            "description": self.description,
            "active_rules": [r.to_dict() for r in self.active_rules],
            "custom_rules": [r.to_dict() for r in self.custom_rules],
            "version": self.version,
            "author": self.author,
            "enforce_base_rules": self.enforce_base_rules,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Ruleset:
        """Deserialize ruleset from storage."""
        return cls(
            ruleset_id=data["ruleset_id"],
            name=data["name"],
            description=data.get("description", ""),
            active_rules=[RuleInstance.from_dict(r) for r in data.get("active_rules", [])],
            custom_rules=[CustomRule.from_dict(r) for r in data.get("custom_rules", [])],
            version=data.get("version", "1.0"),
            author=data.get("author", ""),
            enforce_base_rules=data.get("enforce_base_rules", True),
        )
    
    def to_json(self) -> str:
        """Export as JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> Ruleset:
        """Import from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def save(self, path: str | Path):
        """Save ruleset to file."""
        path = Path(path)
        path.write_text(self.to_json())
    
    @classmethod
    def load(cls, path: str | Path) -> Ruleset:
        """Load ruleset from file."""
        path = Path(path)
        return cls.from_json(path.read_text())


# ─────────────────────────────────────────────────────────────────────────────
# Preset Rulesets
# ─────────────────────────────────────────────────────────────────────────────

def create_default_ruleset() -> Ruleset:
    """Create a default ruleset with standard D&D 5e rules."""
    ruleset = Ruleset(
        ruleset_id="default_5e",
        name="D&D 5e Standard",
        description="Standard D&D 5th Edition rules",
        enforce_base_rules=True,
    )
    
    # Add standard combat rules
    ruleset.add_rule("skill_check", skill="Perception", dc=10)
    ruleset.add_rule("is_alive")
    ruleset.add_rule("can_take_action")
    
    return ruleset


def create_minimal_ruleset() -> Ruleset:
    """Create a minimal ruleset (base rules only)."""
    return Ruleset(
        ruleset_id="minimal",
        name="Minimal",
        description="Only base rules, no optional rules",
        enforce_base_rules=True,
    )


def create_dungeon_crawl_ruleset() -> Ruleset:
    """Create a ruleset optimized for dungeon exploration."""
    ruleset = Ruleset(
        ruleset_id="dungeon_crawl",
        name="Dungeon Crawl",
        description="Rules for dungeon exploration with trap support",
        enforce_base_rules=True,
    )
    
    # Add perception checks for traps
    ruleset.add_rule("skill_check", skill="Perception", dc=15)
    ruleset.add_rule("skill_check", skill="Investigation", dc=12)
    
    # Movement rules
    ruleset.add_rule("tile_passable")
    ruleset.add_rule("tile_not_occupied")
    ruleset.add_rule("has_movement", required=5)
    
    return ruleset


# ─────────────────────────────────────────────────────────────────────────────
# Ruleset Manager
# ─────────────────────────────────────────────────────────────────────────────

class RulesetManager:
    """
    Manages rulesets for a project/scenario.
    
    Handles:
    - Loading/saving rulesets
    - Preset ruleset library
    - Active ruleset for current scenario
    """
    
    def __init__(self, storage_path: str | Path | None = None):
        self._rulesets: dict[str, Ruleset] = {}
        self._active_ruleset_id: str | None = None
        self._storage_path = Path(storage_path) if storage_path else None
        
        # Register preset rulesets
        self._register_presets()
    
    def _register_presets(self):
        """Register built-in presets."""
        self.register(create_default_ruleset())
        self.register(create_minimal_ruleset())
        self.register(create_dungeon_crawl_ruleset())
    
    def register(self, ruleset: Ruleset):
        """Register a ruleset."""
        self._rulesets[ruleset.ruleset_id] = ruleset
    
    def get(self, ruleset_id: str) -> Ruleset | None:
        """Get a ruleset by ID."""
        return self._rulesets.get(ruleset_id)
    
    def get_all(self) -> list[Ruleset]:
        """Get all rulesets."""
        return list(self._rulesets.values())
    
    def set_active(self, ruleset_id: str):
        """Set the active ruleset for the current scenario."""
        if ruleset_id in self._rulesets:
            self._active_ruleset_id = ruleset_id
    
    def get_active(self) -> Ruleset | None:
        """Get the currently active ruleset."""
        if self._active_ruleset_id:
            return self._rulesets.get(self._active_ruleset_id)
        return None
    
    def create_ruleset(
        self, 
        name: str, 
        description: str = "",
        copy_from: str | None = None
    ) -> Ruleset:
        """
        Create a new ruleset.
        
        Args:
            name: Display name
            description: Description
            copy_from: Optional ruleset ID to copy from
        
        Returns:
            New Ruleset
        """
        import uuid
        
        ruleset_id = f"custom_{uuid.uuid4().hex[:8]}"
        
        if copy_from and copy_from in self._rulesets:
            # Copy existing ruleset
            source = self._rulesets[copy_from]
            ruleset = Ruleset.from_dict(source.to_dict())
            ruleset.ruleset_id = ruleset_id
            ruleset.name = name
            ruleset.description = description
        else:
            ruleset = Ruleset(
                ruleset_id=ruleset_id,
                name=name,
                description=description,
            )
        
        self.register(ruleset)
        return ruleset
    
    def delete(self, ruleset_id: str):
        """Delete a ruleset."""
        if ruleset_id in self._rulesets:
            del self._rulesets[ruleset_id]
            if self._active_ruleset_id == ruleset_id:
                self._active_ruleset_id = None
    
    def save_all(self):
        """Save all rulesets to storage."""
        if not self._storage_path:
            return
        
        self._storage_path.mkdir(parents=True, exist_ok=True)
        
        for ruleset in self._rulesets.values():
            path = self._storage_path / f"{ruleset.ruleset_id}.json"
            ruleset.save(path)
    
    def load_all(self):
        """Load all rulesets from storage."""
        if not self._storage_path or not self._storage_path.exists():
            return
        
        for path in self._storage_path.glob("*.json"):
            try:
                ruleset = Ruleset.load(path)
                self.register(ruleset)
            except Exception as e:
                print(f"Failed to load ruleset {path}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Integration with Triggers
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TriggerRuleBinding:
    """
    Binds a ruleset to a trigger.
    
    This allows triggers to use configurable rules.
    """
    trigger_id: str
    ruleset: Ruleset
    
    # Which rules from the ruleset to use as pre_specs
    pre_spec_rule_ids: list[str] = field(default_factory=list)
    
    # Which custom rules to use
    pre_spec_custom_ids: list[str] = field(default_factory=list)
    
    def build_pre_specs(self, registry: RuleRegistry) -> list[Specification]:
        """Build pre_specs from the configured rules."""
        specs = []
        
        for rule_id in self.pre_spec_rule_ids:
            instance = self.ruleset.get_rule(rule_id)
            if instance:
                spec = instance.create_spec(registry)
                if spec:
                    specs.append(spec)
        
        for custom_id in self.pre_spec_custom_ids:
            for custom in self.ruleset.custom_rules:
                if custom.instance_id == custom_id:
                    spec = custom.create_spec(registry)
                    if spec:
                        specs.append(spec)
        
        return specs

"""
Rule Builder - Declarative Custom Rule Creation

This module provides the "mask" system for creating rules without code:
- RuleBuilder: Fluent API for constructing specs
- RuleMask: Template for custom rule types
- CompositeBuilder: Combine multiple rules with AND/OR/NOT

The goal is to let users create custom rules through a UI form
that generates valid specifications.

Example:
    # Create a custom trap rule via builder
    builder = RuleBuilder()
    trap_spec = (
        builder
        .when_event("enter_tile")
        .require_entity_type("player")
        .require_skill_check_fails("Perception", dc=15)
        .build()
    )
    
    # Or from a saved mask
    mask = RuleMask.from_dict(saved_data)
    spec = mask.instantiate(custom_params)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum
import json

from domain.specs.base import (
    Specification, SpecResult, AlwaysTrue, AlwaysFalse,
    AndSpec, OrSpec, NotSpec, AllOf, AnyOf
)
from domain.specs.registry import RuleDefinition, RuleParameter, RuleCategory, RuleScope


class CompositionType(Enum):
    """How to combine multiple conditions."""
    AND = "and"      # All must pass
    OR = "or"        # At least one must pass
    SEQUENCE = "sequence"  # Evaluated in order, short-circuit on failure


@dataclass
class RuleComponent:
    """
    A single component in a rule definition.
    
    Represents one spec with its configuration.
    """
    rule_id: str              # Reference to registered rule
    params: dict[str, Any]    # Parameter values
    inverted: bool = False    # Apply NOT to this component
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "params": self.params,
            "inverted": self.inverted,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuleComponent:
        return cls(
            rule_id=data["rule_id"],
            params=data.get("params", {}),
            inverted=data.get("inverted", False),
        )


@dataclass
class RuleMask:
    """
    A template for creating custom rules.
    
    This is the "mask" - a saved configuration that can be
    instantiated into a Specification. Users create these
    through the UI, and they're saved as JSON.
    
    Attributes:
        mask_id: Unique identifier for this mask
        name: Display name
        description: What this rule does
        components: List of rule components to combine
        composition: How to combine components (AND/OR)
        category: For organization in the UI
        parameters: User-configurable parameters (override component params)
    """
    mask_id: str
    name: str
    description: str
    components: list[RuleComponent]
    composition: CompositionType = CompositionType.AND
    category: RuleCategory = RuleCategory.CUSTOM
    
    # Parameters exposed to users of this mask
    exposed_parameters: list[RuleParameter] = field(default_factory=list)
    
    # Metadata
    author: str = ""
    version: str = "1.0"
    tags: list[str] = field(default_factory=list)
    
    def instantiate(
        self, 
        registry: "RuleRegistry",
        **overrides: Any
    ) -> Specification:
        """
        Create a Specification from this mask.
        
        Args:
            registry: RuleRegistry to look up component rules
            **overrides: Parameter values to override defaults
        
        Returns:
            Composed Specification
        """
        specs: list[Specification] = []
        
        for component in self.components:
            # Get the rule definition
            rule_def = registry.get(component.rule_id)
            if rule_def is None:
                raise ValueError(f"Unknown rule: {component.rule_id}")
            
            # Merge parameters: component params + overrides
            params = dict(component.params)
            
            # Apply exposed parameter overrides
            for param in self.exposed_parameters:
                if param.name in overrides:
                    # Map exposed param to component param
                    params[param.name] = overrides[param.name]
            
            # Create the spec
            spec = rule_def.create_spec(**params)
            
            # Apply inversion if needed
            if component.inverted:
                spec = ~spec
            
            specs.append(spec)
        
        # Compose specs
        if len(specs) == 0:
            return AlwaysTrue()
        elif len(specs) == 1:
            return specs[0]
        elif self.composition == CompositionType.AND:
            return AllOf(*specs, short_circuit=True)
        elif self.composition == CompositionType.OR:
            return AnyOf(*specs, short_circuit=True)
        else:  # SEQUENCE
            return AllOf(*specs, short_circuit=True)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize mask for storage."""
        return {
            "mask_id": self.mask_id,
            "name": self.name,
            "description": self.description,
            "components": [c.to_dict() for c in self.components],
            "composition": self.composition.value,
            "category": self.category.value,
            "exposed_parameters": [p.to_dict() for p in self.exposed_parameters],
            "author": self.author,
            "version": self.version,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuleMask:
        """Deserialize mask from storage."""
        return cls(
            mask_id=data["mask_id"],
            name=data["name"],
            description=data["description"],
            components=[RuleComponent.from_dict(c) for c in data["components"]],
            composition=CompositionType(data.get("composition", "and")),
            category=RuleCategory(data.get("category", "custom")),
            exposed_parameters=[RuleParameter.from_dict(p) for p in data.get("exposed_parameters", [])],
            author=data.get("author", ""),
            version=data.get("version", "1.0"),
            tags=data.get("tags", []),
        )
    
    def to_json(self) -> str:
        """Export as JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> RuleMask:
        """Import from JSON string."""
        return cls.from_dict(json.loads(json_str))


class RuleBuilder:
    """
    Fluent builder for creating specifications.
    
    Provides a chainable API for constructing rules step-by-step.
    Used by the UI to build rules interactively.
    
    Example:
        spec = (
            RuleBuilder()
            .require("is_alive")
            .require("skill_check", skill="Perception", dc=15, inverted=True)
            .require("is_entity_type", entity_type="player")
            .with_composition(CompositionType.AND)
            .build(registry)
        )
    """
    
    def __init__(self):
        self._components: list[RuleComponent] = []
        self._composition = CompositionType.AND
        self._name = "Custom Rule"
        self._description = ""
    
    def require(
        self, 
        rule_id: str, 
        inverted: bool = False,
        **params: Any
    ) -> RuleBuilder:
        """
        Add a requirement (spec) to this rule.
        
        Args:
            rule_id: ID of registered rule
            inverted: If True, applies NOT to this requirement
            **params: Parameters for the rule
        
        Returns:
            self for chaining
        """
        self._components.append(RuleComponent(
            rule_id=rule_id,
            params=params,
            inverted=inverted,
        ))
        return self
    
    def require_not(self, rule_id: str, **params: Any) -> RuleBuilder:
        """Shorthand for require(..., inverted=True)."""
        return self.require(rule_id, inverted=True, **params)
    
    # ─── Convenience Methods ─────────────────────────────────────────────────
    
    def require_skill_check(self, skill: str, dc: int) -> RuleBuilder:
        """Require a skill check to pass."""
        return self.require("skill_check", skill=skill, dc=dc)
    
    def require_skill_check_fails(self, skill: str, dc: int) -> RuleBuilder:
        """Require a skill check to FAIL (for traps)."""
        return self.require("skill_check", skill=skill, dc=dc, inverted=True)
    
    def require_saving_throw(self, ability: str, dc: int) -> RuleBuilder:
        """Require a saving throw to pass."""
        return self.require("saving_throw", ability=ability, dc=dc)
    
    def require_entity_type(self, entity_type: str) -> RuleBuilder:
        """Require entity to be of a specific type."""
        return self.require("is_entity_type", entity_type=entity_type)
    
    def require_alive(self) -> RuleBuilder:
        """Require entity to be alive."""
        return self.require("is_alive")
    
    def require_can_act(self) -> RuleBuilder:
        """Require entity can take actions."""
        return self.require("can_take_action")
    
    def require_in_range(self, max_range: int, min_range: int = 0) -> RuleBuilder:
        """Require target to be within range."""
        return self.require("in_range", max_range=max_range, min_range=min_range)
    
    def require_adjacent(self) -> RuleBuilder:
        """Require target to be adjacent (5ft)."""
        return self.require("is_adjacent")
    
    def require_has_condition(self, condition: str) -> RuleBuilder:
        """Require entity to have a condition."""
        return self.require("has_condition", condition=condition)
    
    def require_not_condition(self, condition: str) -> RuleBuilder:
        """Require entity to NOT have a condition."""
        return self.require("has_condition", condition=condition, inverted=True)
    
    def require_has_movement(self, feet: int = 5) -> RuleBuilder:
        """Require entity to have movement remaining."""
        return self.require("has_movement", required=feet)
    
    def require_has_spell_slot(self, level: int) -> RuleBuilder:
        """Require entity to have a spell slot."""
        return self.require("has_spell_slot", level=level)
    
    # ─── Configuration ───────────────────────────────────────────────────────
    
    def with_composition(self, composition: CompositionType) -> RuleBuilder:
        """Set how components are combined."""
        self._composition = composition
        return self
    
    def combine_with_and(self) -> RuleBuilder:
        """Combine components with AND (all must pass)."""
        return self.with_composition(CompositionType.AND)
    
    def combine_with_or(self) -> RuleBuilder:
        """Combine components with OR (any must pass)."""
        return self.with_composition(CompositionType.OR)
    
    def named(self, name: str) -> RuleBuilder:
        """Set the rule name."""
        self._name = name
        return self
    
    def described(self, description: str) -> RuleBuilder:
        """Set the rule description."""
        self._description = description
        return self
    
    # ─── Build ───────────────────────────────────────────────────────────────
    
    def build(self, registry: "RuleRegistry") -> Specification:
        """
        Build the final Specification.
        
        Args:
            registry: RuleRegistry to look up component rules
        
        Returns:
            Composed Specification
        """
        mask = self.to_mask()
        return mask.instantiate(registry)
    
    def to_mask(self, mask_id: str | None = None) -> RuleMask:
        """
        Export as a RuleMask for storage.
        
        Args:
            mask_id: Unique ID for the mask (auto-generated if not provided)
        
        Returns:
            RuleMask that can be serialized
        """
        import uuid
        
        return RuleMask(
            mask_id=mask_id or f"custom_{uuid.uuid4().hex[:8]}",
            name=self._name,
            description=self._description,
            components=list(self._components),
            composition=self._composition,
        )
    
    def clear(self) -> RuleBuilder:
        """Clear all components and start fresh."""
        self._components.clear()
        self._name = "Custom Rule"
        self._description = ""
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Preset Templates (Common Rule Patterns)
# ─────────────────────────────────────────────────────────────────────────────

def trap_template(
    name: str,
    skill: str,
    dc: int,
    description: str = "",
) -> RuleMask:
    """
    Create a standard trap mask.
    
    Triggers when: Player enters tile AND fails skill check
    """
    return RuleMask(
        mask_id=f"trap_{name.lower().replace(' ', '_')}",
        name=name,
        description=description or f"Trap: {skill} DC {dc}",
        components=[
            RuleComponent("is_entity_type", {"entity_type": "player"}),
            RuleComponent("skill_check", {"skill": skill, "dc": dc}, inverted=True),
        ],
        composition=CompositionType.AND,
        category=RuleCategory.TRAPS,
        exposed_parameters=[
            RuleParameter("dc", "int", "Difficulty Class", default=dc, min_value=1, max_value=30),
        ],
        tags=["trap", skill.lower()],
    )


def zone_effect_template(
    name: str,
    entity_types: list[str] | None = None,
    description: str = "",
) -> RuleMask:
    """
    Create a zone effect mask (triggers on entry, no check required).
    """
    components = []
    
    if entity_types:
        # Require one of the entity types (OR)
        for etype in entity_types:
            components.append(RuleComponent("is_entity_type", {"entity_type": etype}))
    
    return RuleMask(
        mask_id=f"zone_{name.lower().replace(' ', '_')}",
        name=name,
        description=description or f"Zone effect: {name}",
        components=components,
        composition=CompositionType.OR if len(components) > 1 else CompositionType.AND,
        category=RuleCategory.ENVIRONMENTAL,
        tags=["zone", "environmental"],
    )


def combat_prerequisite_template(
    name: str,
    requires_action: bool = True,
    requires_reaction: bool = False,
    max_range: int | None = None,
    description: str = "",
) -> RuleMask:
    """
    Create a combat action prerequisite mask.
    """
    components = [
        RuleComponent("is_alive", {}),
        RuleComponent("is_incapacitated", {}, inverted=True),  # NOT incapacitated
    ]
    
    if requires_action:
        components.append(RuleComponent("can_take_action", {}))
    
    if requires_reaction:
        components.append(RuleComponent("can_take_reaction", {}))
    
    if max_range is not None:
        components.append(RuleComponent("in_range", {"max_range": max_range}))
    
    return RuleMask(
        mask_id=f"combat_{name.lower().replace(' ', '_')}",
        name=name,
        description=description or f"Combat prerequisite: {name}",
        components=components,
        composition=CompositionType.AND,
        category=RuleCategory.COMBAT,
        tags=["combat", "prerequisite"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Mask Library (Predefined Templates)
# ─────────────────────────────────────────────────────────────────────────────

class MaskLibrary:
    """
    Collection of predefined rule masks.
    
    Users can browse these as starting points for custom rules.
    """
    
    def __init__(self):
        self._masks: dict[str, RuleMask] = {}
        self._register_defaults()
    
    def _register_defaults(self):
        """Register built-in mask templates."""
        
        # Traps
        self.register(trap_template(
            "Pit Trap",
            skill="Perception",
            dc=15,
            description="A hidden pit trap. Falling creatures take damage.",
        ))
        
        self.register(trap_template(
            "Poison Dart Trap",
            skill="Perception",
            dc=12,
            description="Darts shoot from the wall when triggered.",
        ))
        
        self.register(trap_template(
            "Pressure Plate",
            skill="Investigation",
            dc=14,
            description="A pressure plate that triggers when stepped on.",
        ))
        
        # Combat prerequisites
        self.register(combat_prerequisite_template(
            "Melee Attack",
            requires_action=True,
            max_range=5,
            description="Prerequisites for making a melee attack.",
        ))
        
        self.register(combat_prerequisite_template(
            "Opportunity Attack",
            requires_action=False,
            requires_reaction=True,
            max_range=5,
            description="Prerequisites for making an opportunity attack.",
        ))
        
        self.register(combat_prerequisite_template(
            "Ranged Attack (30ft)",
            requires_action=True,
            max_range=30,
            description="Prerequisites for a short-range ranged attack.",
        ))
        
        # Zone effects
        self.register(zone_effect_template(
            "Healing Zone",
            entity_types=["player", "npc"],
            description="Area that heals friendly creatures.",
        ))
        
        self.register(zone_effect_template(
            "Damage Zone",
            entity_types=["player", "enemy", "npc"],
            description="Area that damages all creatures.",
        ))
    
    def register(self, mask: RuleMask):
        """Add a mask to the library."""
        self._masks[mask.mask_id] = mask
    
    def get(self, mask_id: str) -> RuleMask | None:
        """Get a mask by ID."""
        return self._masks.get(mask_id)
    
    def get_all(self) -> list[RuleMask]:
        """Get all masks."""
        return list(self._masks.values())
    
    def get_by_category(self, category: RuleCategory) -> list[RuleMask]:
        """Get masks in a category."""
        return [m for m in self._masks.values() if m.category == category]
    
    def search(self, query: str) -> list[RuleMask]:
        """Search masks by name, description, or tags."""
        query = query.lower()
        results = []
        
        for mask in self._masks.values():
            if (query in mask.name.lower() or
                query in mask.description.lower() or
                any(query in tag.lower() for tag in mask.tags)):
                results.append(mask)
        
        return results
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize library."""
        return {
            "masks": {mid: m.to_dict() for mid, m in self._masks.items()}
        }
    
    def export_json(self, path: str):
        """Export to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def from_json(cls, path: str) -> MaskLibrary:
        """Import from JSON file."""
        library = cls()
        library._masks.clear()
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        for mask_data in data.get("masks", {}).values():
            library.register(RuleMask.from_dict(mask_data))
        
        return library


# ─────────────────────────────────────────────────────────────────────────────
# Global Instances
# ─────────────────────────────────────────────────────────────────────────────

_default_library: MaskLibrary | None = None


def get_default_library() -> MaskLibrary:
    """Get the global mask library."""
    global _default_library
    if _default_library is None:
        _default_library = MaskLibrary()
    return _default_library

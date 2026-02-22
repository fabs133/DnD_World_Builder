"""
Migration Adapter: Bridge Legacy Conditions to Specifications

This module provides adapters to use the new specification system
alongside the existing condition/trigger code, enabling gradual migration.

Migration Strategy:
1. Add this adapter layer
2. Wrap existing conditions with LegacyConditionAdapter
3. Gradually replace with native specs
4. Remove adapters when migration complete

Usage:
    from domain.specs.migration import adapt_legacy_condition
    
    # Wrap existing AlwaysTrue condition
    old_condition = AlwaysTrue()
    spec = adapt_legacy_condition(old_condition, "always_true")
    
    # Use in new trigger system
    trigger = TriggerSpec(
        trigger_id="migrated_trap",
        event_type=EventType.ENTER_TILE,
        pre_specs=[spec],
        reaction=my_reaction,
    )
"""

from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

from domain.specs.base import Specification, SpecResult


class LegacyConditionAdapter(Specification):
    """
    Wraps a legacy condition callable as a Specification.
    
    Legacy conditions have signature: (event_data: dict) -> bool
    This adapter converts them to the new SpecResult-based system.
    
    Args:
        condition: The legacy condition (callable returning bool)
        rule_id: Identifier for this condition
        description: Human-readable description for messages
    """
    
    def __init__(
        self,
        condition: Callable[[dict], bool],
        rule_id: str,
        description: str = "Legacy condition",
        suggested_fix: str | None = None,
    ):
        self._condition = condition
        self._rule_id = rule_id
        self._description = description
        self._suggested_fix = suggested_fix
    
    @property
    def rule_id(self) -> str:
        return self._rule_id
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        """
        Evaluate the legacy condition.
        
        The candidate is passed as 'entity' in the event_data dict,
        and context is merged in for compatibility.
        """
        # Build event_data dict that legacy conditions expect
        event_data = dict(context or {})
        
        # Add candidate to event_data if it has attributes legacy code expects
        if hasattr(candidate, "__dict__"):
            for key, value in candidate.__dict__.items():
                if key not in event_data:
                    event_data[key] = value
        
        # Also try common attribute patterns
        if hasattr(candidate, "stats"):
            event_data["character_stats"] = candidate.stats
        if hasattr(candidate, "skill_modifiers"):
            event_data["character_stats"] = candidate.skill_modifiers
        
        try:
            passed = self._condition(event_data)
        except Exception as e:
            return SpecResult(
                rule_id=self._rule_id,
                passed=False,
                message=f"Legacy condition error: {e}",
                suggested_fix="Check condition implementation",
                tags=frozenset({"legacy", "error"}),
                data={"error": str(e)}
            )
        
        return SpecResult(
            rule_id=self._rule_id,
            passed=passed,
            message=f"{self._description}: {'passed' if passed else 'failed'}",
            suggested_fix=None if passed else self._suggested_fix,
            tags=frozenset({"legacy"}),
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "LegacyConditionAdapter",
            "rule_id": self._rule_id,
            "description": self._description,
            # Note: The actual condition callable is not serializable
        }


class LegacySkillCheckAdapter(Specification):
    """
    Wraps the legacy SkillCheck class as a Specification.
    
    Legacy SkillCheck has:
        - attempt(character_stats, advantage=False, disadvantage=False) -> bool
        - Rolls dice internally
    
    This adapter:
        - Takes roll from context (for determinism)
        - Falls back to calling attempt() if no roll provided
    """
    
    def __init__(self, legacy_skill_check: Any):
        """
        Args:
            legacy_skill_check: Instance of models.flow.skill_check.SkillCheck
        """
        self._skill_check = legacy_skill_check
    
    @property
    def rule_id(self) -> str:
        return f"legacy_skill_check_{self._skill_check.skill_name.lower()}_dc{self._skill_check.dc}"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        context = context or {}
        
        # Get character stats
        character_stats = {}
        if hasattr(candidate, "stats"):
            character_stats = candidate.stats
        elif hasattr(candidate, "skill_modifiers"):
            character_stats = candidate.skill_modifiers
        elif "character_stats" in context:
            character_stats = context["character_stats"]
        
        # Check for advantage/disadvantage
        advantage = context.get("advantage", False)
        disadvantage = context.get("disadvantage", False)
        
        # If roll is provided in context, calculate result deterministically
        if "roll" in context:
            roll = context["roll"]
            modifier = character_stats.get(self._skill_check.skill_name, 0)
            total = roll + modifier
            passed = total >= self._skill_check.dc
            
            return SpecResult(
                rule_id=self.rule_id,
                passed=passed,
                message=f"{self._skill_check.skill_name}: {roll}+{modifier}={total} vs DC {self._skill_check.dc}",
                suggested_fix=None if passed else f"Roll {self._skill_check.dc - modifier}+ on d20",
                tags=frozenset({"legacy", "skill_check", self._skill_check.skill_name.lower()}),
                data={
                    "skill": self._skill_check.skill_name,
                    "dc": self._skill_check.dc,
                    "roll": roll,
                    "modifier": modifier,
                    "total": total,
                }
            )
        
        # Fall back to legacy behavior (rolls dice)
        passed = self._skill_check.attempt(
            character_stats,
            advantage=advantage,
            disadvantage=disadvantage
        )
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=passed,
            message=f"{self._skill_check.skill_name} check vs DC {self._skill_check.dc}: {'passed' if passed else 'failed'}",
            tags=frozenset({"legacy", "skill_check", "nondeterministic"}),
            data={
                "skill": self._skill_check.skill_name,
                "dc": self._skill_check.dc,
                "warning": "Result was rolled, not deterministic",
            }
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "LegacySkillCheckAdapter",
            "skill_name": self._skill_check.skill_name,
            "dc": self._skill_check.dc,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Factory Functions
# ─────────────────────────────────────────────────────────────────────────────

def adapt_legacy_condition(
    condition: Any,
    rule_id: str | None = None,
    description: str | None = None,
) -> Specification:
    """
    Factory to wrap any legacy condition as a Specification.
    
    Automatically detects condition type and uses appropriate adapter.
    
    Args:
        condition: Legacy condition (AlwaysTrue, PerceptionCheck, SkillCheck, etc.)
        rule_id: Optional custom rule_id (auto-generated if not provided)
        description: Optional description for messages
    
    Returns:
        Specification wrapping the legacy condition
    """
    condition_class = condition.__class__.__name__
    
    # Handle SkillCheck specially (has attempt() method)
    if hasattr(condition, "attempt") and hasattr(condition, "skill_name"):
        return LegacySkillCheckAdapter(condition)
    
    # Generate default rule_id from class name
    if rule_id is None:
        rule_id = f"legacy_{condition_class.lower()}"
        # Add DC if present
        if hasattr(condition, "dc"):
            rule_id += f"_dc{condition.dc}"
    
    # Generate description
    if description is None:
        description = condition_class
        if hasattr(condition, "dc"):
            description += f" (DC {condition.dc})"
    
    # Wrap callable conditions
    if callable(condition):
        return LegacyConditionAdapter(
            condition=condition,
            rule_id=rule_id,
            description=description,
        )
    
    raise TypeError(f"Cannot adapt condition of type {condition_class}")


def adapt_legacy_trigger(legacy_trigger: Any) -> "TriggerSpec":
    """
    Convert a legacy Trigger to a TriggerSpec.
    
    Legacy Trigger has:
        - event_type: str
        - condition: callable or object with __call__
        - reaction: callable
        - next_trigger: optional Trigger
        - cooldown: int
        - label: str
    
    Returns:
        TriggerSpec using adapted conditions
    """
    from domain.specs.triggers import TriggerSpec, EventType, ReactionResult
    
    # Adapt the condition
    pre_specs = []
    if hasattr(legacy_trigger, "condition") and legacy_trigger.condition is not None:
        adapted = adapt_legacy_condition(legacy_trigger.condition)
        pre_specs.append(adapted)
    
    # Wrap the reaction
    def wrapped_reaction(entity: Any, context: dict) -> ReactionResult:
        if hasattr(legacy_trigger, "reaction") and legacy_trigger.reaction is not None:
            # Call legacy reaction with event_data format
            event_data = dict(context)
            if hasattr(entity, "__dict__"):
                event_data.update(entity.__dict__)
            
            legacy_trigger.reaction(event_data)
            
            return ReactionResult(
                success=True,
                description=f"Legacy reaction executed",
            )
        return ReactionResult(success=True, description="No reaction defined")
    
    # Handle chained triggers
    next_trigger = None
    if hasattr(legacy_trigger, "next_trigger") and legacy_trigger.next_trigger is not None:
        next_trigger = adapt_legacy_trigger(legacy_trigger.next_trigger)
    
    # Map event type
    event_type_str = getattr(legacy_trigger, "event_type", "custom")
    try:
        event_type = EventType(event_type_str.lower())
    except ValueError:
        event_type = EventType.CUSTOM
    
    return TriggerSpec(
        trigger_id=getattr(legacy_trigger, "label", "legacy_trigger") or "legacy_trigger",
        event_type=event_type,
        pre_specs=pre_specs,
        reaction=wrapped_reaction,
        next_trigger=next_trigger,
        cooldown_turns=getattr(legacy_trigger, "cooldown", 0),
        label=getattr(legacy_trigger, "label", ""),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Registry for Spec Deserialization
# ─────────────────────────────────────────────────────────────────────────────

class SpecRegistry:
    """
    Registry for deserializing specifications from dicts.
    
    Specs register themselves by type name, allowing polymorphic
    deserialization from JSON/dict data.
    
    Usage:
        registry = SpecRegistry()
        registry.register("SkillCheckSpec", SkillCheckSpec)
        
        data = {"type": "SkillCheckSpec", "skill": "Perception", "dc": 15}
        spec = registry.from_dict(data)
    """
    
    def __init__(self):
        self._specs: dict[str, type[Specification]] = {}
        self._register_builtins()
    
    def _register_builtins(self):
        """Register built-in spec types."""
        from domain.specs.base import AlwaysTrue, AlwaysFalse
        from domain.specs.checks import SkillCheckSpec, SavingThrowSpec, ContestSpec
        from domain.specs.movement import (
            HasMovementRemaining, TileIsPassable, TileNotOccupied, InRange
        )
        from domain.specs.entity import (
            HasCondition, IsIncapacitated, IsAlive, HasHP,
            HasSpellSlot, IsEntityType, CanTakeAction
        )
        
        builtins = [
            AlwaysTrue, AlwaysFalse,
            SkillCheckSpec, SavingThrowSpec, ContestSpec,
            HasMovementRemaining, TileIsPassable, TileNotOccupied, InRange,
            HasCondition, IsIncapacitated, IsAlive, HasHP,
            HasSpellSlot, IsEntityType, CanTakeAction,
        ]
        
        for spec_class in builtins:
            self.register(spec_class.__name__, spec_class)
    
    def register(self, type_name: str, spec_class: type[Specification]):
        """Register a spec type for deserialization."""
        self._specs[type_name] = spec_class
    
    def from_dict(self, data: dict[str, Any]) -> Specification:
        """
        Deserialize a specification from a dict.
        
        Handles composite specs (AndSpec, OrSpec, etc.) recursively.
        """
        type_name = data.get("type")
        
        if type_name is None:
            raise ValueError("Spec dict must have 'type' field")
        
        # Handle composite specs
        if type_name == "AndSpec":
            left = self.from_dict(data["left"])
            right = self.from_dict(data["right"])
            return left & right
        
        if type_name == "OrSpec":
            left = self.from_dict(data["left"])
            right = self.from_dict(data["right"])
            return left | right
        
        if type_name == "NotSpec":
            inner = self.from_dict(data["inner"])
            return ~inner
        
        if type_name == "AllOf":
            specs = [self.from_dict(s) for s in data["specs"]]
            from domain.specs.base import AllOf
            return AllOf(*specs, short_circuit=data.get("short_circuit", False))
        
        if type_name == "AnyOf":
            specs = [self.from_dict(s) for s in data["specs"]]
            from domain.specs.base import AnyOf
            return AnyOf(*specs, short_circuit=data.get("short_circuit", True))
        
        # Look up registered spec type
        if type_name not in self._specs:
            raise ValueError(f"Unknown spec type: {type_name}")
        
        spec_class = self._specs[type_name]
        return spec_class.from_dict(data)


# Global registry instance
_registry = SpecRegistry()


def get_registry() -> SpecRegistry:
    """Get the global spec registry."""
    return _registry


def spec_from_dict(data: dict[str, Any]) -> Specification:
    """Convenience function to deserialize a spec using the global registry."""
    return _registry.from_dict(data)

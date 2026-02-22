"""
D&D 5e Entity Condition and Status Specifications

This module implements entity state checks:
- Condition effects (incapacitated, prone, invisible, etc.)
- Resource availability (HP, spell slots, abilities)
- Combat state (in combat, surprised, etc.)

These specs check the state of an entity without modifying it.
"""

from __future__ import annotations

from typing import Any
from enum import Enum

from domain.specs.base import Specification, SpecResult


class Condition(Enum):
    """D&D 5e conditions."""
    BLINDED = "blinded"
    CHARMED = "charmed"
    DEAFENED = "deafened"
    FRIGHTENED = "frightened"
    GRAPPLED = "grappled"
    INCAPACITATED = "incapacitated"
    INVISIBLE = "invisible"
    PARALYZED = "paralyzed"
    PETRIFIED = "petrified"
    POISONED = "poisoned"
    PRONE = "prone"
    RESTRAINED = "restrained"
    STUNNED = "stunned"
    UNCONSCIOUS = "unconscious"
    EXHAUSTION_1 = "exhaustion_1"
    EXHAUSTION_2 = "exhaustion_2"
    EXHAUSTION_3 = "exhaustion_3"
    EXHAUSTION_4 = "exhaustion_4"
    EXHAUSTION_5 = "exhaustion_5"
    EXHAUSTION_6 = "exhaustion_6"


# Conditions that prevent taking actions
INCAPACITATING_CONDITIONS = {
    Condition.INCAPACITATED,
    Condition.PARALYZED,
    Condition.PETRIFIED,
    Condition.STUNNED,
    Condition.UNCONSCIOUS,
}

# Conditions that impose disadvantage on attack rolls
ATTACK_DISADVANTAGE_CONDITIONS = {
    Condition.BLINDED,
    Condition.FRIGHTENED,  # When source is visible
    Condition.POISONED,
    Condition.PRONE,
    Condition.RESTRAINED,
}


class HasCondition(Specification):
    """
    Check if entity has a specific condition.
    
    Args:
        condition: The condition to check for
    """
    
    def __init__(self, condition: Condition | str):
        if isinstance(condition, str):
            condition = Condition(condition)
        self.condition = condition
    
    @property
    def rule_id(self) -> str:
        return f"has_condition_{self.condition.value}"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        conditions = self._get_conditions(candidate)
        has_it = self.condition in conditions or self.condition.value in conditions
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=has_it,
            message=f"{'Has' if has_it else 'Does not have'} {self.condition.value}",
            tags=frozenset({"condition", self.condition.value}),
            data={"condition": self.condition.value, "all_conditions": [c.value if isinstance(c, Condition) else c for c in conditions]}
        )
    
    def _get_conditions(self, candidate: Any) -> set:
        if hasattr(candidate, "conditions"):
            return set(candidate.conditions)
        if isinstance(candidate, dict):
            return set(candidate.get("conditions", []))
        return set()
    
    def to_dict(self) -> dict[str, Any]:
        return {"type": "HasCondition", "condition": self.condition.value}
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HasCondition:
        return cls(condition=data["condition"])


class IsIncapacitated(Specification):
    """
    Check if entity is incapacitated (can't take actions).
    
    This checks for any condition that causes incapacitation:
    - Incapacitated
    - Paralyzed
    - Petrified
    - Stunned
    - Unconscious
    """
    
    @property
    def rule_id(self) -> str:
        return "is_incapacitated"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        conditions = self._get_conditions(candidate)
        
        blocking_condition = None
        for cond in INCAPACITATING_CONDITIONS:
            if cond in conditions or cond.value in conditions:
                blocking_condition = cond
                break
        
        if blocking_condition:
            return SpecResult(
                rule_id=self.rule_id,
                passed=True,
                message=f"Incapacitated due to {blocking_condition.value}",
                tags=frozenset({"condition", "incapacitated", blocking_condition.value}),
                data={"blocking_condition": blocking_condition.value}
            )
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=False,
            message="Not incapacitated",
            tags=frozenset({"condition"}),
        )
    
    def _get_conditions(self, candidate: Any) -> set:
        if hasattr(candidate, "conditions"):
            return set(candidate.conditions)
        if isinstance(candidate, dict):
            return set(candidate.get("conditions", []))
        return set()
    
    def to_dict(self) -> dict[str, Any]:
        return {"type": "IsIncapacitated"}


class IsAlive(Specification):
    """
    Check if entity is alive (HP > 0 and not dead).
    """
    
    @property
    def rule_id(self) -> str:
        return "is_alive"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        hp = self._get_hp(candidate)
        is_dead = self._is_dead(candidate)
        
        if is_dead:
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message="Entity is dead",
                suggested_fix="Use Revivify or Raise Dead",
                tags=frozenset({"hp", "death"}),
                data={"hp": hp, "is_dead": True}
            )
        
        if hp <= 0:
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message=f"HP at {hp} (unconscious or dying)",
                suggested_fix="Provide healing or stabilize",
                tags=frozenset({"hp", "unconscious"}),
                data={"hp": hp, "is_dead": False}
            )
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=True,
            message=f"Alive with {hp} HP",
            tags=frozenset({"hp"}),
            data={"hp": hp}
        )
    
    def _get_hp(self, candidate: Any) -> int:
        if hasattr(candidate, "hp"):
            return candidate.hp
        if hasattr(candidate, "current_hp"):
            return candidate.current_hp
        if isinstance(candidate, dict):
            return candidate.get("hp", candidate.get("current_hp", 0))
        return 0
    
    def _is_dead(self, candidate: Any) -> bool:
        if hasattr(candidate, "is_dead"):
            return candidate.is_dead
        if isinstance(candidate, dict):
            return candidate.get("is_dead", False)
        return False
    
    def to_dict(self) -> dict[str, Any]:
        return {"type": "IsAlive"}


class HasHP(Specification):
    """
    Check if entity has at least a certain amount of HP.
    
    Args:
        minimum: Minimum HP required
    """
    
    def __init__(self, minimum: int = 1):
        self.minimum = minimum
    
    @property
    def rule_id(self) -> str:
        return f"has_hp_{self.minimum}"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        hp = self._get_hp(candidate)
        max_hp = self._get_max_hp(candidate)
        passed = hp >= self.minimum
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=passed,
            message=f"HP: {hp}/{max_hp} (need {self.minimum})",
            suggested_fix=None if passed else f"Need {self.minimum - hp} more HP",
            tags=frozenset({"hp", "resource"}),
            data={
                "current_hp": hp,
                "max_hp": max_hp,
                "required": self.minimum,
                "deficit": max(0, self.minimum - hp),
            }
        )
    
    def _get_hp(self, candidate: Any) -> int:
        if hasattr(candidate, "hp"):
            return candidate.hp
        if hasattr(candidate, "current_hp"):
            return candidate.current_hp
        if isinstance(candidate, dict):
            return candidate.get("hp", candidate.get("current_hp", 0))
        return 0
    
    def _get_max_hp(self, candidate: Any) -> int:
        if hasattr(candidate, "max_hp"):
            return candidate.max_hp
        if isinstance(candidate, dict):
            return candidate.get("max_hp", 0)
        return 0
    
    def to_dict(self) -> dict[str, Any]:
        return {"type": "HasHP", "minimum": self.minimum}


class HasSpellSlot(Specification):
    """
    Check if entity has a spell slot of the required level.
    
    Args:
        level: Spell slot level required (1-9)
    """
    
    def __init__(self, level: int):
        if not 1 <= level <= 9:
            raise ValueError(f"Spell slot level must be 1-9, got {level}")
        self.level = level
    
    @property
    def rule_id(self) -> str:
        return f"has_spell_slot_{self.level}"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        slots = self._get_spell_slots(candidate)
        available = slots.get(self.level, 0)
        passed = available > 0
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=passed,
            message=f"Level {self.level} slots: {available}",
            suggested_fix=None if passed else f"Take a long rest or use higher slot",
            tags=frozenset({"spellcasting", "resource", f"level_{self.level}"}),
            data={
                "level": self.level,
                "available": available,
                "all_slots": slots,
            }
        )
    
    def _get_spell_slots(self, candidate: Any) -> dict[int, int]:
        if hasattr(candidate, "spell_slots"):
            return dict(candidate.spell_slots)
        if isinstance(candidate, dict):
            return candidate.get("spell_slots", {})
        return {}
    
    def to_dict(self) -> dict[str, Any]:
        return {"type": "HasSpellSlot", "level": self.level}


class HasAbilityUse(Specification):
    """
    Check if entity has uses remaining of a specific ability.
    
    Args:
        ability_name: Name of the ability (e.g., "Second Wind", "Action Surge")
    """
    
    def __init__(self, ability_name: str):
        self.ability_name = ability_name
    
    @property
    def rule_id(self) -> str:
        return f"has_ability_use_{self.ability_name.lower().replace(' ', '_')}"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        uses = self._get_ability_uses(candidate)
        available = uses.get(self.ability_name, 0)
        passed = available > 0
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=passed,
            message=f"{self.ability_name}: {available} uses remaining",
            suggested_fix=None if passed else f"Take a rest to regain {self.ability_name}",
            tags=frozenset({"ability", "resource", self.ability_name.lower()}),
            data={
                "ability": self.ability_name,
                "available": available,
            }
        )
    
    def _get_ability_uses(self, candidate: Any) -> dict[str, int]:
        if hasattr(candidate, "ability_uses"):
            return dict(candidate.ability_uses)
        if isinstance(candidate, dict):
            return candidate.get("ability_uses", {})
        return {}
    
    def to_dict(self) -> dict[str, Any]:
        return {"type": "HasAbilityUse", "ability_name": self.ability_name}


class IsEntityType(Specification):
    """
    Check if entity is of a specific type.
    
    Args:
        entity_type: Type to check for (e.g., "player", "enemy", "npc", "trap")
    """
    
    def __init__(self, entity_type: str):
        self.entity_type = entity_type.lower()
    
    @property
    def rule_id(self) -> str:
        return f"is_entity_type_{self.entity_type}"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        actual_type = self._get_type(candidate).lower()
        passed = actual_type == self.entity_type
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=passed,
            message=f"Entity type is {actual_type} (checking for {self.entity_type})",
            tags=frozenset({"entity_type", self.entity_type}),
            data={"expected": self.entity_type, "actual": actual_type}
        )
    
    def _get_type(self, candidate: Any) -> str:
        if hasattr(candidate, "entity_type"):
            return candidate.entity_type
        if isinstance(candidate, dict):
            return candidate.get("entity_type", "unknown")
        return "unknown"
    
    def to_dict(self) -> dict[str, Any]:
        return {"type": "IsEntityType", "entity_type": self.entity_type}


class HasFaction(Specification):
    """
    Check if entity belongs to a specific faction.
    
    Args:
        faction: Faction to check for
    """
    
    def __init__(self, faction: str):
        self.faction = faction.lower()
    
    @property
    def rule_id(self) -> str:
        return f"has_faction_{self.faction}"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        actual_faction = self._get_faction(candidate).lower()
        passed = actual_faction == self.faction
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=passed,
            message=f"Faction is {actual_faction}",
            tags=frozenset({"faction", actual_faction}),
            data={"expected": self.faction, "actual": actual_faction}
        )
    
    def _get_faction(self, candidate: Any) -> str:
        if hasattr(candidate, "faction"):
            return candidate.faction
        if isinstance(candidate, dict):
            return candidate.get("faction", "neutral")
        return "neutral"
    
    def to_dict(self) -> dict[str, Any]:
        return {"type": "HasFaction", "faction": self.faction}


# ─────────────────────────────────────────────────────────────────────────────
# Combat State Specifications
# ─────────────────────────────────────────────────────────────────────────────

class CanTakeAction(Specification):
    """
    Check if entity can take an action on their turn.
    
    Checks for incapacitation and action economy.
    """
    
    @property
    def rule_id(self) -> str:
        return "can_take_action"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        # First check if incapacitated
        incap_spec = IsIncapacitated()
        incap_result = incap_spec.is_satisfied_by(candidate, context)
        
        if incap_result.passed:  # IsIncapacitated returns True if incapacitated
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message=incap_result.message,
                suggested_fix="Remove incapacitating condition",
                tags=frozenset({"action", "incapacitated"}),
                data={"reason": "incapacitated", "condition": incap_result.data.get("blocking_condition")}
            )
        
        # Check if action already used
        action_used = self._action_used(candidate, context)
        if action_used:
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message="Action already used this turn",
                suggested_fix="Wait for next turn or use Action Surge",
                tags=frozenset({"action", "resource"}),
                data={"reason": "action_used"}
            )
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=True,
            message="Can take action",
            tags=frozenset({"action"}),
        )
    
    def _action_used(self, candidate: Any, context: dict[str, Any] | None) -> bool:
        if context and context.get("action_used"):
            return True
        if hasattr(candidate, "action_used"):
            return candidate.action_used
        return False
    
    def to_dict(self) -> dict[str, Any]:
        return {"type": "CanTakeAction"}


class CanTakeBonusAction(Specification):
    """Check if entity can take a bonus action."""
    
    @property
    def rule_id(self) -> str:
        return "can_take_bonus_action"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        context = context or {}
        
        # Check incapacitation
        incap_spec = IsIncapacitated()
        if incap_spec.is_satisfied_by(candidate, context):
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message="Cannot take bonus action while incapacitated",
                tags=frozenset({"bonus_action", "incapacitated"}),
            )
        
        # Check if already used
        bonus_used = context.get("bonus_action_used") or getattr(candidate, "bonus_action_used", False)
        if bonus_used:
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message="Bonus action already used this turn",
                tags=frozenset({"bonus_action", "resource"}),
            )
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=True,
            message="Can take bonus action",
            tags=frozenset({"bonus_action"}),
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {"type": "CanTakeBonusAction"}


class CanTakeReaction(Specification):
    """Check if entity can take a reaction."""
    
    @property
    def rule_id(self) -> str:
        return "can_take_reaction"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        context = context or {}
        
        # Check incapacitation
        incap_spec = IsIncapacitated()
        if incap_spec.is_satisfied_by(candidate, context):
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message="Cannot take reaction while incapacitated",
                tags=frozenset({"reaction", "incapacitated"}),
            )
        
        # Check if already used
        reaction_used = context.get("reaction_used") or getattr(candidate, "reaction_used", False)
        if reaction_used:
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message="Reaction already used since last turn",
                suggested_fix="Wait until start of next turn",
                tags=frozenset({"reaction", "resource"}),
            )
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=True,
            message="Can take reaction",
            tags=frozenset({"reaction"}),
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {"type": "CanTakeReaction"}

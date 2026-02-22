"""
D&D 5e Trigger Specifications

This module implements the trigger system using specifications:
- Triggers are evaluated using composable specs
- Full traceability of what fired and why
- Support for chained triggers
- Cooldown tracking

This replaces the old callback-based trigger system with a pure,
traceable specification-based approach.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum

from domain.specs.base import Specification, SpecResult, AllOf


class EventType(Enum):
    """Standard D&D trigger events."""
    ENTER_TILE = "enter_tile"
    EXIT_TILE = "exit_tile"
    START_TURN = "start_turn"
    END_TURN = "end_turn"
    TAKE_DAMAGE = "take_damage"
    DEAL_DAMAGE = "deal_damage"
    CAST_SPELL = "cast_spell"
    ATTACK = "attack"
    ATTACKED = "attacked"
    DEATH = "death"
    PERCEPTION_CHECK = "perception_check"
    INTERACT = "interact"
    CUSTOM = "custom"


@dataclass(frozen=True)
class TriggerEvent:
    """
    An event that can fire triggers.
    
    This is the data passed to trigger evaluation.
    """
    event_type: EventType | str
    source_entity_id: str | None = None
    target_tile_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            "source_entity_id": self.source_entity_id,
            "target_tile_id": self.target_tile_id,
            "data": self.data,
        }


@dataclass(frozen=True)
class ReactionResult:
    """
    Result of executing a trigger's reaction.
    
    Reactions are side-effectful operations, so this captures
    what happened for tracing and potential rollback.
    """
    success: bool
    description: str
    effects: list[dict[str, Any]] = field(default_factory=list)
    damage_dealt: int = 0
    healing_done: int = 0
    conditions_applied: list[str] = field(default_factory=list)
    entities_spawned: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "description": self.description,
            "effects": self.effects,
            "damage_dealt": self.damage_dealt,
            "healing_done": self.healing_done,
            "conditions_applied": list(self.conditions_applied),
            "entities_spawned": list(self.entities_spawned),
        }


@dataclass(frozen=True)
class TriggerEvaluation:
    """
    Complete record of a trigger evaluation.
    
    This is the traceable output from checking a trigger,
    whether it fired or not.
    """
    trigger_id: str
    event: TriggerEvent
    spec_results: list[SpecResult]
    fired: bool
    reaction_result: ReactionResult | None = None
    chain_evaluations: list["TriggerEvaluation"] = field(default_factory=list)
    
    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.spec_results)
    
    @property
    def failed_specs(self) -> list[SpecResult]:
        return [r for r in self.spec_results if not r.passed]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_id": self.trigger_id,
            "event": self.event.to_dict(),
            "spec_results": [r.to_dict() for r in self.spec_results],
            "fired": self.fired,
            "reaction_result": self.reaction_result.to_dict() if self.reaction_result else None,
            "chain_evaluations": [e.to_dict() for e in self.chain_evaluations],
        }


class TriggerSpec:
    """
    A trigger defined using specifications.
    
    This is the new way to define triggers:
    - pre_specs: Must all pass for trigger to fire
    - post_specs: Validate reaction results
    - reaction: The effect when trigger fires
    - next_trigger: Optional chained trigger
    
    Example:
        # Pit trap: Perception check to notice, else take damage
        trap = TriggerSpec(
            trigger_id="pit_trap_1",
            event_type=EventType.ENTER_TILE,
            pre_specs=[
                ~SkillCheckSpec("Perception", dc=15),  # Fires when FAILS
                IsEntityType("player"),  # Only affects players
            ],
            reaction=lambda entity, context: ReactionResult(
                success=True,
                description="You fall into a pit!",
                damage_dealt=10,
            ),
            cooldown_turns=0,  # Can fire every time
        )
    """
    
    def __init__(
        self,
        trigger_id: str,
        event_type: EventType | str,
        pre_specs: list[Specification] | None = None,
        post_specs: list[Specification] | None = None,
        reaction: Callable[[Any, dict], ReactionResult] | None = None,
        next_trigger: "TriggerSpec | None" = None,
        cooldown_turns: int = 0,
        label: str = "",
        description: str = "",
    ):
        self.trigger_id = trigger_id
        self.event_type = event_type if isinstance(event_type, EventType) else EventType(event_type)
        self.pre_specs = pre_specs or []
        self.post_specs = post_specs or []
        self.reaction = reaction
        self.next_trigger = next_trigger
        self.cooldown_turns = cooldown_turns
        self.label = label or trigger_id
        self.description = description
        
        # Runtime state (mutable, not serialized)
        self._cooldown_remaining = 0
    
    def evaluate(
        self,
        event: TriggerEvent,
        entity: Any,
        context: dict[str, Any] | None = None,
    ) -> TriggerEvaluation:
        """
        Evaluate whether this trigger should fire for the given event.
        
        This method is PURE except for cooldown tracking.
        Returns a full trace of the evaluation.
        
        Args:
            event: The triggering event
            entity: The entity that triggered the event
            context: Additional context (tile state, roll results, etc.)
        
        Returns:
            TriggerEvaluation with complete trace
        """
        context = context or {}
        context["event"] = event
        
        # Check cooldown first
        if self._cooldown_remaining > 0:
            return TriggerEvaluation(
                trigger_id=self.trigger_id,
                event=event,
                spec_results=[
                    SpecResult(
                        rule_id="cooldown_check",
                        passed=False,
                        message=f"On cooldown for {self._cooldown_remaining} more turns",
                        tags=frozenset({"cooldown"}),
                        data={"remaining": self._cooldown_remaining}
                    )
                ],
                fired=False,
            )
        
        # Evaluate all pre_specs
        spec_results: list[SpecResult] = []
        
        for spec in self.pre_specs:
            result = spec.is_satisfied_by(entity, context)
            spec_results.append(result)
        
        all_passed = all(r.passed for r in spec_results)
        
        if not all_passed:
            return TriggerEvaluation(
                trigger_id=self.trigger_id,
                event=event,
                spec_results=spec_results,
                fired=False,
            )
        
        # All specs passed - execute reaction
        reaction_result = None
        if self.reaction:
            reaction_result = self.reaction(entity, context)
            
            # Start cooldown
            if self.cooldown_turns > 0:
                self._cooldown_remaining = self.cooldown_turns
        
        # Evaluate post_specs if present
        if self.post_specs and reaction_result:
            post_context = {**context, "reaction_result": reaction_result}
            for spec in self.post_specs:
                post_result = spec.is_satisfied_by(entity, post_context)
                spec_results.append(post_result)
        
        # Chain to next trigger if present
        chain_evaluations = []
        if self.next_trigger and reaction_result and reaction_result.success:
            chain_eval = self.next_trigger.evaluate(event, entity, context)
            chain_evaluations.append(chain_eval)
        
        return TriggerEvaluation(
            trigger_id=self.trigger_id,
            event=event,
            spec_results=spec_results,
            fired=True,
            reaction_result=reaction_result,
            chain_evaluations=chain_evaluations,
        )
    
    def advance_cooldown(self):
        """Call at end of turn to decrement cooldown."""
        if self._cooldown_remaining > 0:
            self._cooldown_remaining -= 1
    
    def reset_cooldown(self):
        """Reset cooldown (e.g., after long rest)."""
        self._cooldown_remaining = 0
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize trigger definition (not runtime state)."""
        return {
            "trigger_id": self.trigger_id,
            "event_type": self.event_type.value,
            "pre_specs": [s.to_dict() for s in self.pre_specs],
            "post_specs": [s.to_dict() for s in self.post_specs],
            "next_trigger": self.next_trigger.to_dict() if self.next_trigger else None,
            "cooldown_turns": self.cooldown_turns,
            "label": self.label,
            "description": self.description,
        }


class TriggerEvaluator:
    """
    Evaluates triggers for a scenario.
    
    This replaces EventBus for trigger evaluation, providing:
    - Centralized trigger management
    - Full traceability
    - No global state
    
    Usage:
        evaluator = TriggerEvaluator()
        evaluator.register(trap_trigger)
        
        event = TriggerEvent(EventType.ENTER_TILE, entity_id, tile_id)
        evaluations = evaluator.evaluate_all(event, entity, context)
        
        for eval in evaluations:
            if eval.fired:
                apply_reaction(eval.reaction_result)
    """
    
    def __init__(self):
        self._triggers: dict[str, TriggerSpec] = {}
        self._by_event_type: dict[EventType, list[str]] = {}
    
    def register(self, trigger: TriggerSpec):
        """Register a trigger."""
        self._triggers[trigger.trigger_id] = trigger
        
        if trigger.event_type not in self._by_event_type:
            self._by_event_type[trigger.event_type] = []
        self._by_event_type[trigger.event_type].append(trigger.trigger_id)
    
    def unregister(self, trigger_id: str):
        """Remove a trigger."""
        if trigger_id in self._triggers:
            trigger = self._triggers.pop(trigger_id)
            if trigger.event_type in self._by_event_type:
                self._by_event_type[trigger.event_type].remove(trigger_id)
    
    def get(self, trigger_id: str) -> TriggerSpec | None:
        """Get a trigger by ID."""
        return self._triggers.get(trigger_id)
    
    def evaluate_all(
        self,
        event: TriggerEvent,
        entity: Any,
        context: dict[str, Any] | None = None,
    ) -> list[TriggerEvaluation]:
        """
        Evaluate all triggers for an event type.
        
        Returns evaluations for ALL triggers, including ones that didn't fire.
        This provides complete traceability.
        """
        event_type = event.event_type if isinstance(event.event_type, EventType) else EventType(event.event_type)
        trigger_ids = self._by_event_type.get(event_type, [])
        
        evaluations = []
        for trigger_id in trigger_ids:
            trigger = self._triggers[trigger_id]
            evaluation = trigger.evaluate(event, entity, context)
            evaluations.append(evaluation)
        
        return evaluations
    
    def evaluate_fired_only(
        self,
        event: TriggerEvent,
        entity: Any,
        context: dict[str, Any] | None = None,
    ) -> list[TriggerEvaluation]:
        """
        Evaluate triggers and return only those that fired.
        
        Use this when you don't need the full trace.
        """
        return [e for e in self.evaluate_all(event, entity, context) if e.fired]
    
    def advance_all_cooldowns(self):
        """Advance cooldowns for all triggers (call at end of round)."""
        for trigger in self._triggers.values():
            trigger.advance_cooldown()
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize all triggers."""
        return {
            "triggers": {tid: t.to_dict() for tid, t in self._triggers.items()}
        }


# ─────────────────────────────────────────────────────────────────────────────
# Common Trigger Patterns
# ─────────────────────────────────────────────────────────────────────────────

def perception_trap(
    trigger_id: str,
    perception_dc: int,
    damage: int,
    damage_type: str = "piercing",
    description: str = "A hidden trap",
) -> TriggerSpec:
    """
    Factory for a standard perception-based trap.
    
    Fires when a player FAILS the perception check.
    """
    from domain.specs.checks import SkillCheckSpec
    from domain.specs.entity import IsEntityType
    
    return TriggerSpec(
        trigger_id=trigger_id,
        event_type=EventType.ENTER_TILE,
        pre_specs=[
            ~SkillCheckSpec("Perception", dc=perception_dc),  # Fires on failure
            IsEntityType("player"),
        ],
        reaction=lambda entity, ctx: ReactionResult(
            success=True,
            description=f"{description} - {damage} {damage_type} damage!",
            damage_dealt=damage,
            effects=[{"type": "damage", "amount": damage, "damage_type": damage_type}],
        ),
        label=f"Trap: {description}",
        description=f"DC {perception_dc} Perception or take {damage} {damage_type} damage",
    )


def enter_zone_trigger(
    trigger_id: str,
    zone_effect: str,
    message: str,
) -> TriggerSpec:
    """
    Factory for a zone-entry trigger (no check required).
    """
    return TriggerSpec(
        trigger_id=trigger_id,
        event_type=EventType.ENTER_TILE,
        pre_specs=[],  # Always fires on entry
        reaction=lambda entity, ctx: ReactionResult(
            success=True,
            description=message,
            effects=[{"type": "zone", "effect": zone_effect}],
        ),
        label=f"Zone: {zone_effect}",
    )

"""Spec-validated action execution with structured results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.specs.base import SpecResult
from domain.specs.entity import CanTakeAction, IsAlive
from models.flow.action.action import Action


@dataclass
class ActionResult:
    """Structured result of attempting an action."""

    success: bool
    action: Action
    spec_results: list[SpecResult] = field(default_factory=list)
    execution_log: list[str] = field(default_factory=list)
    error: str | None = None
    data: dict[str, Any] = field(default_factory=dict)  #: Payload returned by ``action.execute()``


class ActionExecutor:
    """Validates actions against specs, then executes them."""

    def __init__(self, ruleset=None):
        self._ruleset = ruleset

    def execute(
        self,
        action: Action,
        actor: Any,
        game_state: Any,
        context: dict[str, Any] | None = None,
    ) -> ActionResult:
        """Validate and execute an action.

        1. Build spec chain for this action type
        2. Evaluate all specs
        3. Check the action's own rules via ``action.validate()``
        4. If all pass, call action.execute()
        5. Return structured ActionResult
        """
        spec_results = self.validate_only(action, actor, game_state, context)
        failures = [r for r in spec_results if not r.passed]

        if failures:
            return ActionResult(
                success=False,
                action=action,
                spec_results=spec_results,
                execution_log=[f"Validation failed: {f.message}" for f in failures],
                error=failures[0].message,
            )

        # Action-level rules (path, range, speed). Only an explicit False rejects:
        # the base Action.validate() returns None.
        if action.validate(game_state) is False:
            log = list(action.execution_log)
            return ActionResult(
                success=False,
                action=action,
                spec_results=spec_results,
                execution_log=log,
                error=log[-1] if log else f"{action.__class__.__name__} is not valid",
            )

        try:
            data = action.execute(game_state) or {}
            return ActionResult(
                success=True,
                action=action,
                spec_results=spec_results,
                execution_log=list(action.execution_log),
                data=data,
            )
        except Exception as exc:
            return ActionResult(
                success=False,
                action=action,
                spec_results=spec_results,
                execution_log=list(action.execution_log),
                error=str(exc),
            )

    def validate_only(
        self,
        action: Action,
        actor: Any,
        game_state: Any,
        context: dict[str, Any] | None = None,
    ) -> list[SpecResult]:
        """Validate without executing. For AI look-ahead."""
        specs = self._build_specs(action)
        results = []
        for spec in specs:
            result = spec.is_satisfied_by(actor, context)
            results.append(result)
        return results

    def get_available_actions(self, actor: Any, game_state: Any) -> list[str]:
        """List action types the actor could legally take right now."""
        available = []
        alive_spec = IsAlive()
        alive_result = alive_spec.is_satisfied_by(actor)
        if not alive_result.passed:
            return []

        can_act = CanTakeAction()
        act_result = can_act.is_satisfied_by(actor)
        if act_result.passed:
            available.extend(["ATTACK", "MOVE", "DASH", "DODGE", "CAST_SPELL"])

        available.append("END_TURN")
        return available

    def _build_specs(self, action: Action) -> list:
        """Build the spec chain for this action type.

        When a :class:`~domain.specs.ruleset.Ruleset` is configured, its
        enabled rules are evaluated in addition to the base entity checks.
        """
        if self._ruleset is not None:
            from domain.specs.registry import get_default_registry
            registry = get_default_registry()
            return self._ruleset.build_all_specs(registry)

        return [IsAlive(), CanTakeAction()]

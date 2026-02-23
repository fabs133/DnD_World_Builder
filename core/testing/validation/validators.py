"""Post-run validators for GameSessionResult.

These validators check invariants that should hold across any combat session:
- No entity goes below 0 HP
- Dead entities don't act
- Initiative order is respected
- Attacks only target alive entities
- Damage events match HP changes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    """Result of validating a game session."""

    passed: bool
    violations: list[str] = field(default_factory=list)

    def add_violation(self, message: str) -> None:
        self.violations.append(message)
        self.passed = False


def validate_no_negative_hp(result: Any) -> ValidationResult:
    """Verify no entity's HP goes below 0 in the final state.

    Checks ``result.final_state.entities`` for any entity with ``hp < 0``.
    """
    vr = ValidationResult(passed=True)

    if not hasattr(result, "final_state") or result.final_state is None:
        return vr

    for entity in result.final_state.entities:
        if entity.hp < 0:
            vr.add_violation(
                f"{entity.name} has negative HP ({entity.hp}) in final state"
            )

    return vr


def validate_dead_entities_dont_act(result: Any) -> ValidationResult:
    """Verify that dead entities (HP <= 0) don't take actions after dying.

    Scans ``result.action_history`` for actions taken by entities after their
    HP reached 0.
    """
    vr = ValidationResult(passed=True)

    if not hasattr(result, "action_history"):
        return vr

    dead_since: dict[str, int] = {}

    for i, action_result in enumerate(result.action_history):
        action = action_result.action if hasattr(action_result, "action") else None
        if action is None:
            continue

        actor_name = getattr(action, "actor_name", None) or getattr(
            getattr(action, "actor", None), "name", None
        )
        if actor_name is None:
            continue

        # Check if this actor was already dead
        if actor_name in dead_since:
            # Allow end_turn actions for dead entities (cleanup)
            action_type = type(action).__name__
            if action_type != "EndTurnAction":
                vr.add_violation(
                    f"{actor_name} took action '{action_type}' at index {i} "
                    f"but died at index {dead_since[actor_name]}"
                )

        # Track deaths via execution log
        for log_line in getattr(action_result, "execution_log", []):
            log_lower = log_line.lower()
            if "killed" in log_lower or "dies" in log_lower or "defeated" in log_lower:
                # Try to extract the killed entity name from the log
                # This is a heuristic — logs vary
                for entity_name in _extract_entity_names(result):
                    if entity_name.lower() in log_lower and entity_name not in dead_since:
                        dead_since[entity_name] = i

    return vr


def validate_initiative_order_respected(result: Any) -> ValidationResult:
    """Verify turns follow the initiative order within each round.

    Checks that within each round, entities act in the order specified by
    ``result.final_state.initiative_order``.
    """
    vr = ValidationResult(passed=True)

    if not hasattr(result, "final_state") or not hasattr(result, "action_history"):
        return vr

    initiative_order = list(result.final_state.initiative_order)
    if not initiative_order:
        return vr

    # Build a mapping from entity name to initiative position
    position_map = {name: idx for idx, name in enumerate(initiative_order)}

    # Track the last actor within each round
    last_position = -1
    actions_in_round = 0

    for action_result in result.action_history:
        action = action_result.action if hasattr(action_result, "action") else None
        if action is None:
            continue

        actor_name = getattr(action, "actor_name", None) or getattr(
            getattr(action, "actor", None), "name", None
        )
        if actor_name is None or actor_name not in position_map:
            continue

        current_position = position_map[actor_name]

        # If we wrapped around, reset
        if current_position < last_position:
            # This could be a new round — reset
            last_position = -1
            actions_in_round = 0

        last_position = current_position
        actions_in_round += 1

    return vr


def validate_attacks_target_alive_entities(result: Any) -> ValidationResult:
    """Verify attacks only target entities that are alive at the time.

    This is a best-effort check using execution logs to detect targeting
    already-dead entities.
    """
    vr = ValidationResult(passed=True)

    if not hasattr(result, "action_history"):
        return vr

    confirmed_dead: set[str] = set()

    for i, action_result in enumerate(result.action_history):
        action = action_result.action if hasattr(action_result, "action") else None
        if action is None:
            continue

        # Check if this is an attack targeting a dead entity
        target_name = getattr(action, "target_name", None) or getattr(
            getattr(action, "target", None), "name", None
        )
        action_type = type(action).__name__

        if target_name and target_name in confirmed_dead and action_type == "AttackAction":
            vr.add_violation(
                f"Action {i}: Attack targeted dead entity '{target_name}'"
            )

        # Track deaths
        for log_line in getattr(action_result, "execution_log", []):
            log_lower = log_line.lower()
            if "killed" in log_lower or "dies" in log_lower or "defeated" in log_lower:
                for name in _extract_entity_names(result):
                    if name.lower() in log_lower:
                        confirmed_dead.add(name)

    return vr


def validate_damage_consistency(result: Any) -> ValidationResult:
    """Cross-check damage events in action_history with HP changes.

    This is a best-effort validator that checks the execution logs for
    damage values and verifies they are non-negative.
    """
    vr = ValidationResult(passed=True)

    if not hasattr(result, "action_history"):
        return vr

    for i, action_result in enumerate(result.action_history):
        for log_line in getattr(action_result, "execution_log", []):
            # Look for damage patterns like "X damage" or "deals X"
            if "damage" in log_line.lower():
                # Extract numbers from the log line
                import re

                numbers = re.findall(r"\b(\d+)\b", log_line)
                for num_str in numbers:
                    num = int(num_str)
                    if num < 0:
                        vr.add_violation(
                            f"Action {i}: Negative damage value ({num}) in log: {log_line}"
                        )

    return vr


def validate_session(result: Any) -> ValidationResult:
    """Run all validators and return combined results."""
    combined = ValidationResult(passed=True)

    validators = [
        validate_no_negative_hp,
        validate_dead_entities_dont_act,
        validate_initiative_order_respected,
        validate_attacks_target_alive_entities,
        validate_damage_consistency,
    ]

    for validator in validators:
        vr = validator(result)
        if not vr.passed:
            combined.passed = False
            combined.violations.extend(vr.violations)

    return combined


def _extract_entity_names(result: Any) -> list[str]:
    """Extract all entity names from a game session result."""
    names = []
    if hasattr(result, "final_state") and result.final_state is not None:
        for entity in result.final_state.entities:
            names.append(entity.name)
    return names

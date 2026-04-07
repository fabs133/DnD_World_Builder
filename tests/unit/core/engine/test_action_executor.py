"""Tests for the ActionExecutor."""

from unittest.mock import MagicMock

import pytest
from core.engine.action_executor import ActionExecutor, ActionResult
from domain.specs.base import SpecResult, AlwaysFalse
from domain.specs.entity import IsAlive, CanTakeAction
from models.flow.action.action import Action


class MockAction(Action):
    """Simple action for testing."""

    def __init__(self, actor, should_pass=True, execute_result=None):
        super().__init__(actor)
        self._should_pass = should_pass
        self._execute_result = execute_result

    def validate(self, game_state):
        return self._should_pass

    def execute(self, game_state):
        self.execution_log.append("Executed MockAction")
        return self._execute_result or {"action": "mock"}


class FailingAction(Action):
    """Action whose execute raises an exception."""

    def validate(self, game_state):
        return True

    def execute(self, game_state):
        raise RuntimeError("Execution exploded")


class TypeErrorAction(Action):
    """Action whose execute raises a TypeError (programming error)."""

    def validate(self, game_state):
        return True

    def execute(self, game_state):
        raise TypeError("Unexpected type error in execute")


class ValueErrorAction(Action):
    """Action whose execute raises a ValueError."""

    def validate(self, game_state):
        return True

    def execute(self, game_state):
        raise ValueError("Bad value during execution")


class KeyErrorAction(Action):
    """Action whose execute raises a KeyError."""

    def validate(self, game_state):
        return True

    def execute(self, game_state):
        raise KeyError("missing_key")


class WorldCapturingAction(Action):
    """Action that records whether _world was set before execute."""

    def __init__(self, actor):
        super().__init__(actor)
        self.world_at_execute_time = None

    def validate(self, game_state):
        return True

    def execute(self, game_state):
        self.world_at_execute_time = getattr(self, "_world", None)
        self.execution_log.append("Executed WorldCapturingAction")
        return {"action": "world_capture"}


class FakeMoveAction(Action):
    """Action whose class name is 'MoveAction' for spec-bypass testing.

    We dynamically rename the class so that ``__class__.__name__`` returns
    ``"MoveAction"`` — the exact check performed inside ``_build_specs``.
    """

    def validate(self, game_state):
        return True

    def execute(self, game_state):
        self.execution_log.append("Executed FakeMoveAction")
        return {"action": "move"}


# Rename the class so __class__.__name__ is "MoveAction"
FakeMoveAction.__name__ = "MoveAction"
FakeMoveAction.__qualname__ = "MoveAction"


class FakeEndTurnAction(Action):
    """Action whose class name is 'EndTurnAction' for spec-bypass testing."""

    def validate(self, game_state):
        return True

    def execute(self, game_state):
        self.execution_log.append("Executed FakeEndTurnAction")
        return {"action": "end_turn"}


FakeEndTurnAction.__name__ = "EndTurnAction"
FakeEndTurnAction.__qualname__ = "EndTurnAction"


class MockEntity:
    def __init__(self, name="Test", hp=10, conditions=None):
        self.name = name
        self.hp = hp
        self.conditions = conditions or []
        self.entity_type = "player"


class TestActionExecutor:
    def test_execute_success(self):
        executor = ActionExecutor()
        actor = MockEntity(hp=10)
        action = MockAction(actor)
        result = executor.execute(action, actor, game_state=None)

        assert result.success is True
        assert result.error is None

    def test_execute_dead_entity_fails(self):
        executor = ActionExecutor()
        actor = MockEntity(hp=0)
        action = MockAction(actor)
        result = executor.execute(action, actor, game_state=None)

        assert result.success is False
        assert len(result.spec_results) > 0

    def test_execute_incapacitated_entity_fails(self):
        executor = ActionExecutor()
        actor = MockEntity(hp=10, conditions=["stunned"])
        action = MockAction(actor)
        result = executor.execute(action, actor, game_state=None)

        assert result.success is False

    def test_execute_handles_exception(self):
        executor = ActionExecutor()
        actor = MockEntity(hp=10)
        action = FailingAction(actor)
        result = executor.execute(action, actor, game_state=None)

        assert result.success is False
        assert "Execution exploded" in result.error

    def test_validate_only(self):
        executor = ActionExecutor()
        actor = MockEntity(hp=10)
        action = MockAction(actor)
        results = executor.validate_only(action, actor, game_state=None)

        assert len(results) > 0
        assert all(r.passed for r in results)

    def test_get_available_actions_alive(self):
        executor = ActionExecutor()
        actor = MockEntity(hp=10)
        actions = executor.get_available_actions(actor, game_state=None)

        assert "ATTACK" in actions
        assert "MOVE" in actions
        assert "END_TURN" in actions

    def test_get_available_actions_dead(self):
        executor = ActionExecutor()
        actor = MockEntity(hp=0)
        actions = executor.get_available_actions(actor, game_state=None)

        assert actions == []

    def test_action_result_structure(self):
        result = ActionResult(
            success=True,
            action=None,
            spec_results=[],
            execution_log=["did something"],
        )
        assert result.success is True
        assert result.error is None
        assert len(result.execution_log) == 1

    # ── 1. Ruleset integration ──────────────────────────────────────────

    def test_ruleset_specs_used_instead_of_defaults(self):
        """When a ruleset is provided, _build_specs delegates to it."""
        mock_spec = AlwaysFalse(message="Ruleset says no")
        mock_ruleset = MagicMock()
        mock_ruleset.build_all_specs.return_value = [mock_spec]

        executor = ActionExecutor(ruleset=mock_ruleset)
        actor = MockEntity(hp=10)
        action = MockAction(actor)

        results = executor.validate_only(action, actor, game_state=None)

        mock_ruleset.build_all_specs.assert_called_once()
        assert len(results) == 1
        assert results[0].passed is False
        assert results[0].message == "Ruleset says no"

    def test_ruleset_specs_block_execution(self):
        """A failing ruleset spec prevents action.execute() from running."""
        mock_spec = AlwaysFalse(message="Blocked by ruleset")
        mock_ruleset = MagicMock()
        mock_ruleset.build_all_specs.return_value = [mock_spec]

        executor = ActionExecutor(ruleset=mock_ruleset)
        actor = MockEntity(hp=10)
        action = MockAction(actor)

        result = executor.execute(action, actor, game_state=None)

        assert result.success is False
        assert "Blocked by ruleset" in result.error
        # execute() should never have been called
        assert "Executed MockAction" not in result.execution_log

    # ── 2. World context injection ──────────────────────────────────────

    def test_world_context_injected_before_execute(self):
        """action._world is set from context['world'] before execute runs."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10)
        mock_world = MagicMock(name="MockWorld")
        action = WorldCapturingAction(actor)

        result = executor.execute(
            action, actor, game_state=None, context={"world": mock_world}
        )

        assert result.success is True
        assert action.world_at_execute_time is mock_world

    def test_world_context_not_set_when_absent(self):
        """When context has no 'world' key, _world is not set on the action."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10)
        action = WorldCapturingAction(actor)

        result = executor.execute(action, actor, game_state=None, context={})

        assert result.success is True
        assert action.world_at_execute_time is None

    def test_world_context_not_set_when_no_context(self):
        """When context is None, _world is not set on the action."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10)
        action = WorldCapturingAction(actor)

        result = executor.execute(action, actor, game_state=None, context=None)

        assert result.success is True
        assert action.world_at_execute_time is None

    # ── 3. MoveAction / EndTurnAction spec bypass ───────────────────────

    def test_move_action_bypasses_can_take_action_spec(self):
        """MoveAction should only get [IsAlive()], not CanTakeAction."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10)
        action = FakeMoveAction(actor)

        specs = executor._build_specs(action)

        assert len(specs) == 1
        assert isinstance(specs[0], IsAlive)

    def test_end_turn_action_bypasses_can_take_action_spec(self):
        """EndTurnAction should only get [IsAlive()], not CanTakeAction."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10)
        action = FakeEndTurnAction(actor)

        specs = executor._build_specs(action)

        assert len(specs) == 1
        assert isinstance(specs[0], IsAlive)

    def test_regular_action_gets_full_spec_chain(self):
        """A regular action should get [IsAlive(), CanTakeAction()]."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10)
        action = MockAction(actor)

        specs = executor._build_specs(action)

        assert len(specs) == 2
        assert isinstance(specs[0], IsAlive)
        assert isinstance(specs[1], CanTakeAction)

    def test_move_action_succeeds_even_when_incapacitated(self):
        """MoveAction bypasses CanTakeAction, so a stunned but alive entity
        should pass validation (only IsAlive is checked)."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10, conditions=["stunned"])
        action = FakeMoveAction(actor)

        result = executor.execute(action, actor, game_state=None)

        assert result.success is True

    def test_end_turn_succeeds_even_when_incapacitated(self):
        """EndTurnAction bypasses CanTakeAction, so a stunned but alive entity
        should pass validation."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10, conditions=["stunned"])
        action = FakeEndTurnAction(actor)

        result = executor.execute(action, actor, game_state=None)

        assert result.success is True

    # ── 4. get_available_actions with more conditions ───────────────────

    def test_get_available_actions_stunned(self):
        """A stunned entity cannot take actions but gets END_TURN."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10, conditions=["stunned"])
        actions = executor.get_available_actions(actor, game_state=None)

        assert "ATTACK" not in actions
        assert "CAST_SPELL" not in actions
        assert "END_TURN" in actions

    def test_get_available_actions_paralyzed(self):
        """A paralyzed entity cannot take actions but gets END_TURN."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10, conditions=["paralyzed"])
        actions = executor.get_available_actions(actor, game_state=None)

        assert "ATTACK" not in actions
        assert "MOVE" not in actions
        assert "DASH" not in actions
        assert "END_TURN" in actions

    def test_get_available_actions_incapacitated(self):
        """An incapacitated entity cannot take actions but gets END_TURN."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10, conditions=["incapacitated"])
        actions = executor.get_available_actions(actor, game_state=None)

        assert "ATTACK" not in actions
        assert "DODGE" not in actions
        assert "END_TURN" in actions

    def test_get_available_actions_petrified(self):
        """A petrified entity cannot take actions but gets END_TURN."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10, conditions=["petrified"])
        actions = executor.get_available_actions(actor, game_state=None)

        assert "ATTACK" not in actions
        assert "END_TURN" in actions

    def test_get_available_actions_unconscious(self):
        """An unconscious entity cannot take actions but gets END_TURN."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10, conditions=["unconscious"])
        actions = executor.get_available_actions(actor, game_state=None)

        assert "ATTACK" not in actions
        assert "END_TURN" in actions

    def test_get_available_actions_non_incapacitating_condition(self):
        """A poisoned entity (non-incapacitating) can still take all actions."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10, conditions=["poisoned"])
        actions = executor.get_available_actions(actor, game_state=None)

        assert "ATTACK" in actions
        assert "MOVE" in actions
        assert "DASH" in actions
        assert "DODGE" in actions
        assert "CAST_SPELL" in actions
        assert "END_TURN" in actions

    # ── 5. validate_only with failing specs ─────────────────────────────

    def test_validate_only_returns_failures_without_executing(self):
        """validate_only should return failing SpecResults but never call
        action.execute()."""
        executor = ActionExecutor()
        actor = MockEntity(hp=0)  # Dead actor -> IsAlive fails
        action = MockAction(actor)

        results = executor.validate_only(action, actor, game_state=None)

        # At least one failure
        assert any(not r.passed for r in results)
        # execute was never called
        assert len(action.execution_log) == 0

    def test_validate_only_stunned_reports_cannot_take_action(self):
        """validate_only on a stunned entity should report CanTakeAction failure."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10, conditions=["stunned"])
        action = MockAction(actor)

        results = executor.validate_only(action, actor, game_state=None)

        # IsAlive should pass, CanTakeAction should fail
        assert results[0].passed is True  # IsAlive
        assert results[1].passed is False  # CanTakeAction
        assert len(action.execution_log) == 0

    def test_validate_only_dead_entity_fails_at_first_spec(self):
        """validate_only on a dead entity should fail at IsAlive."""
        executor = ActionExecutor()
        actor = MockEntity(hp=0)
        action = MockAction(actor)

        results = executor.validate_only(action, actor, game_state=None)

        failed = [r for r in results if not r.passed]
        assert len(failed) >= 1
        assert failed[0].rule_id == "is_alive"

    # ── 6. Exception narrowing ──────────────────────────────────────────

    def test_type_error_is_caught(self):
        """TypeError in execute() is now caught and returned as failure."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10)
        action = TypeErrorAction(actor)

        result = executor.execute(action, actor, game_state=None)
        assert not result.success
        assert "Unexpected type error in execute" in result.error

    def test_value_error_is_caught(self):
        """ValueError in execute() should be caught and returned as failure."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10)
        action = ValueErrorAction(actor)

        result = executor.execute(action, actor, game_state=None)

        assert result.success is False
        assert "Bad value during execution" in result.error

    def test_key_error_is_caught(self):
        """KeyError in execute() should be caught and returned as failure."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10)
        action = KeyErrorAction(actor)

        result = executor.execute(action, actor, game_state=None)

        assert result.success is False
        assert "missing_key" in result.error

    def test_runtime_error_is_caught(self):
        """RuntimeError in execute() should be caught and returned as failure."""
        executor = ActionExecutor()
        actor = MockEntity(hp=10)
        action = FailingAction(actor)

        result = executor.execute(action, actor, game_state=None)

        assert result.success is False
        assert "Execution exploded" in result.error

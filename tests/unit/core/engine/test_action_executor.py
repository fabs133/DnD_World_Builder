"""Tests for the ActionExecutor."""

import pytest
from core.engine.action_executor import ActionExecutor, ActionResult
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

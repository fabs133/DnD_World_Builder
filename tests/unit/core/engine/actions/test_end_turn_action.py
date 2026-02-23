"""Tests for EndTurnAction."""

from core.engine.actions.end_turn_action import EndTurnAction


class SimpleEntity:
    def __init__(self, name="Test"):
        self.name = name


class TestEndTurnAction:
    def test_always_valid(self):
        action = EndTurnAction(SimpleEntity())
        assert action.validate(None) is True

    def test_execute_returns_end_turn(self):
        action = EndTurnAction(SimpleEntity("Fighter"))
        result = action.execute(None)

        assert result["action"] == "end_turn"
        assert result["actor"] == "Fighter"

    def test_execution_log(self):
        action = EndTurnAction(SimpleEntity("Fighter"))
        action.execute(None)

        assert "Fighter ends turn" in action.execution_log[0]

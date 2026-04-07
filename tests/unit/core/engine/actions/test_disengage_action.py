"""Tests for DisengageAction."""

import pytest
from core.engine.actions.disengage_action import DisengageAction


class SimpleEntity:
    def __init__(self, name, hp=10):
        self.name = name
        self.hp = hp
        self.disengaging = False


class TestDisengageAction:
    def test_validate_alive(self):
        actor = SimpleEntity("Rogue")
        action = DisengageAction(actor)
        assert action.validate(None) is True

    def test_validate_dead(self):
        actor = SimpleEntity("Rogue", hp=0)
        action = DisengageAction(actor)
        assert action.validate(None) is False

    def test_execute_sets_disengaging_flag(self):
        actor = SimpleEntity("Rogue")
        action = DisengageAction(actor)
        result = action.execute(None)
        assert actor.disengaging is True
        assert result["action"] == "disengage"

    def test_execution_log_populated(self):
        actor = SimpleEntity("Rogue")
        action = DisengageAction(actor)
        action.execute(None)
        assert len(action.execution_log) > 0
        assert "Disengage" in action.execution_log[0]

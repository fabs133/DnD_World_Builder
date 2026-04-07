"""Tests for DashAction."""

import pytest
from core.engine.actions.dash_action import DashAction


class SimpleEntity:
    def __init__(self, name, hp=10, speed=30, movement_remaining=30):
        self.name = name
        self.hp = hp
        self.speed = speed
        self.movement_remaining = movement_remaining


class TestDashAction:
    def test_validate_alive(self):
        actor = SimpleEntity("Fighter")
        action = DashAction(actor)
        assert action.validate(None) is True

    def test_validate_dead(self):
        actor = SimpleEntity("Fighter", hp=0)
        action = DashAction(actor)
        assert action.validate(None) is False

    def test_execute_doubles_movement(self):
        actor = SimpleEntity("Fighter", speed=30, movement_remaining=30)
        action = DashAction(actor)
        result = action.execute(None)
        assert actor.movement_remaining == 60
        assert result["action"] == "dash"
        assert result["extra_movement"] == 30

    def test_execute_adds_to_partial_movement(self):
        actor = SimpleEntity("Fighter", speed=30, movement_remaining=10)
        action = DashAction(actor)
        action.execute(None)
        assert actor.movement_remaining == 40

    def test_execute_custom_speed(self):
        actor = SimpleEntity("Monk", speed=45, movement_remaining=45)
        action = DashAction(actor)
        action.execute(None)
        assert actor.movement_remaining == 90

    def test_execution_log_populated(self):
        actor = SimpleEntity("Rogue")
        action = DashAction(actor)
        action.execute(None)
        assert len(action.execution_log) > 0
        assert "dashes" in action.execution_log[0]

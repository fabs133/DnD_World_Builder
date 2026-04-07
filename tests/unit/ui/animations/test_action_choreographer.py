"""Tests for ActionChoreographer."""

import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass, field

from ui.animations.action_choreographer import ActionChoreographer
from ui.animations.choreography_data import MELEE_HIT, MELEE_MISS, SIMPLE_ACTION


@dataclass
class FakeAction:
    actor: MagicMock = None
    target: MagicMock = None

    def __post_init__(self):
        if self.actor is None:
            self.actor = MagicMock()
            self.actor.name = "Fighter"
            self.actor.position = (1, 2)
        if self.target is None:
            self.target = MagicMock()
            self.target.name = "Goblin"
            self.target.position = (1, 3)


FakeAction.__name__ = "AttackAction"
FakeAction.__qualname__ = "AttackAction"


@dataclass
class FakeResult:
    success: bool = True
    action: FakeAction = None
    execution_log: list = field(default_factory=list)
    error: str | None = None
    spec_results: list = field(default_factory=list)

    def __post_init__(self):
        if self.action is None:
            self.action = FakeAction()


class TestExtractContext:
    def test_extracts_actor_name(self):
        ch = ActionChoreographer()
        result = FakeResult(execution_log=["Fighter hits Goblin for 8 damage"])
        ctx = ch._extract_context(result)
        assert ctx["actor_name"] == "Fighter"
        assert ctx["target_name"] == "Goblin"

    def test_extracts_damage(self):
        ch = ActionChoreographer()
        result = FakeResult(execution_log=["Dealt 12 damage (20 -> 8 HP)"])
        ctx = ch._extract_context(result)
        assert ctx["damage"] == "12"

    def test_extracts_crit(self):
        ch = ActionChoreographer()
        result = FakeResult(execution_log=["Critical hit! 16 damage"])
        ctx = ch._extract_context(result)
        assert ctx["is_crit"] is True

    def test_no_actor_returns_none(self):
        ch = ActionChoreographer()
        action = FakeAction()
        action.actor = None
        result = FakeResult(action=action)
        assert ch._extract_context(result) is None


class TestSelectSequence:
    def test_attack_hit(self):
        ch = ActionChoreographer()
        result = FakeResult(
            success=True,
            execution_log=["Fighter hits Goblin for 8 damage"],
        )
        ctx = ch._extract_context(result)
        seq = ch._select_sequence(result, ctx)
        assert seq.name == "melee_hit"

    def test_attack_miss(self):
        ch = ActionChoreographer()
        result = FakeResult(
            success=True,
            execution_log=["Fighter misses Goblin"],
        )
        ctx = ch._extract_context(result)
        seq = ch._select_sequence(result, ctx)
        assert seq.name == "melee_miss"

    def test_attack_crit(self):
        ch = ActionChoreographer()
        result = FakeResult(
            success=True,
            execution_log=["Critical hit! Fighter hits Goblin for 16 damage"],
        )
        ctx = ch._extract_context(result)
        seq = ch._select_sequence(result, ctx)
        assert seq.name == "melee_crit"

    def test_move_action_simple(self):
        ch = ActionChoreographer()
        action = FakeAction()
        action.__class__ = type("MoveAction", (), {})
        action.__class__.__name__ = "MoveAction"
        result = FakeResult(success=True, action=action, execution_log=[])
        ctx = ch._extract_context(result)
        seq = ch._select_sequence(result, ctx)
        assert seq.name == "simple"


class TestPlayLifecycle:
    def test_returns_false_for_none_result(self):
        ch = ActionChoreographer()
        assert ch.play(None) is False

    def test_returns_true_for_valid_result(self):
        ch = ActionChoreographer()
        result = FakeResult(execution_log=["Fighter hits Goblin for 5 damage"])
        started = ch.play(result)
        assert started is True
        assert ch.is_playing is True

    def test_cancel_stops_playing(self):
        ch = ActionChoreographer()
        result = FakeResult(execution_log=["Fighter hits Goblin for 5 damage"])
        ch.play(result)
        ch.cancel()
        assert ch.is_playing is False

    def test_rejects_overlapping_play(self):
        ch = ActionChoreographer()
        result = FakeResult(execution_log=["Fighter hits Goblin for 5 damage"])
        ch.play(result)
        assert ch.play(result) is False  # Still playing

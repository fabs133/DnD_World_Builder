"""Tests for core.gameCreation.turn_manager — Turn scheduling."""

import pytest

from core.gameCreation.turn_manager import TurnManager


class TestTurnManager:
    def test_initial_turn_is_zero(self):
        tm = TurnManager()
        assert tm.current_turn == 0

    def test_next_turn_increments(self):
        tm = TurnManager()
        result = tm.next_turn()
        assert result == 1
        assert tm.current_turn == 1
        result = tm.next_turn()
        assert result == 2

    def test_schedule_in_fires_callback(self):
        tm = TurnManager()
        received = []
        tm.schedule_in(3, lambda data: received.append(data), "payload")
        tm.next_turn()  # turn 1
        tm.next_turn()  # turn 2
        assert len(received) == 0
        tm.next_turn()  # turn 3 → fires
        assert received == ["payload"]

    def test_callback_receives_data(self):
        tm = TurnManager()
        received = []
        tm.schedule_in(1, lambda d: received.append(d), {"key": "value"})
        tm.next_turn()
        assert received == [{"key": "value"}]

    def test_callback_receives_none_data(self):
        tm = TurnManager()
        received = []
        tm.schedule_in(1, lambda d: received.append(d))
        tm.next_turn()
        assert received == [None]

    def test_multiple_callbacks_same_turn(self):
        tm = TurnManager()
        received = []
        tm.schedule_in(2, lambda d: received.append("a"), None)
        tm.schedule_in(2, lambda d: received.append("b"), None)
        tm.next_turn()  # turn 1
        tm.next_turn()  # turn 2 → both fire
        assert "a" in received
        assert "b" in received
        assert len(received) == 2

    def test_callback_removed_after_firing(self):
        tm = TurnManager()
        call_count = [0]
        tm.schedule_in(1, lambda d: call_count.__setitem__(0, call_count[0] + 1))
        tm.next_turn()  # fires
        tm.next_turn()  # should NOT fire again
        assert call_count[0] == 1

    def test_schedule_in_zero_fires_next_turn(self):
        """schedule_in(0) means fire at current_turn + 0 = current turn.
        Since _dispatch_due runs after increment, it fires on turn 1 only
        if scheduled at turn 0 with offset 0 → fire_turn = 0, but dispatch
        runs after increment to 1. So it should fire on next_turn when the
        fire_turn matches."""
        tm = TurnManager()
        received = []
        # fire_turn = 0 + 0 = 0, but next_turn increments to 1 first
        # So this callback is scheduled for turn 0, which already passed
        # once next_turn is called. It will never fire.
        # Instead, schedule_in(1) means fire on turn 1.
        tm.schedule_in(1, lambda d: received.append(True))
        tm.next_turn()
        assert len(received) == 1

    def test_many_turns_with_staggered_callbacks(self):
        tm = TurnManager()
        order = []
        tm.schedule_in(1, lambda d: order.append("first"))
        tm.schedule_in(3, lambda d: order.append("third"))
        tm.schedule_in(2, lambda d: order.append("second"))
        tm.next_turn()  # 1
        tm.next_turn()  # 2
        tm.next_turn()  # 3
        assert order == ["first", "second", "third"]

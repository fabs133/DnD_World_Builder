"""Tests for InputAdapter and TestAdapter."""

import pytest
from core.engine.input_adapter import TestAdapter
from core.engine.game_state import GameState, EntitySnapshot
from models.flow.action.action import Action


class DummyAction(Action):
    def __init__(self, label="dummy"):
        super().__init__(actor=None)
        self.label = label

    def validate(self, game_state):
        return True

    def execute(self, game_state):
        return {"action": self.label}


def _make_state():
    return GameState(
        round_number=1,
        current_entity_name="Test",
        entities=(),
        initiative_order=(),
        world_width=5, world_height=5, tile_type="square",
    )


class TestTestAdapter:
    def test_replays_actions_in_order(self):
        actions = [DummyAction("first"), DummyAction("second"), DummyAction("third")]
        adapter = TestAdapter(action_sequence=actions)
        state = _make_state()

        a1 = adapter.choose_action("E", state, ["ATTACK"])
        assert a1.label == "first"

        a2 = adapter.choose_action("E", state, ["ATTACK"])
        assert a2.label == "second"

        a3 = adapter.choose_action("E", state, ["ATTACK"])
        assert a3.label == "third"

    def test_raises_when_exhausted(self):
        adapter = TestAdapter(action_sequence=[DummyAction()])
        state = _make_state()

        adapter.choose_action("E", state, [])
        with pytest.raises(IndexError, match="ran out of scripted actions"):
            adapter.choose_action("E", state, [])

    def test_replays_targets(self):
        adapter = TestAdapter(target_sequence=["Goblin", "Orc"])
        state = _make_state()

        assert adapter.choose_target("E", state, ["Goblin", "Orc"]) == "Goblin"
        assert adapter.choose_target("E", state, ["Goblin", "Orc"]) == "Orc"

    def test_replays_movements(self):
        adapter = TestAdapter(movement_sequence=[(1, 2), (3, 4)])
        state = _make_state()

        assert adapter.choose_movement("E", state, []) == (1, 2)
        assert adapter.choose_movement("E", state, []) == (3, 4)

    def test_raises_on_empty_targets(self):
        adapter = TestAdapter(target_sequence=[])
        state = _make_state()

        with pytest.raises(IndexError, match="ran out of scripted targets"):
            adapter.choose_target("E", state, [])

    def test_raises_on_empty_movements(self):
        adapter = TestAdapter(movement_sequence=[])
        state = _make_state()

        with pytest.raises(IndexError, match="ran out of scripted movements"):
            adapter.choose_movement("E", state, [])

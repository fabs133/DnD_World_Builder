"""Tests for CLIAdapter interactive terminal input."""

import pytest
from unittest.mock import patch

from core.engine.cli_adapter import CLIAdapter
from core.engine.game_state import GameState, EntitySnapshot
from core.engine.actions.attack_action import AttackAction
from core.engine.actions.move_action import MoveAction
from core.engine.actions.end_turn_action import EndTurnAction


# ── Helpers ──────────────────────────────────────────────────────────────


class SimpleEntity:
    def __init__(self, name, entity_type="player", hp=20, armor_class=12):
        self.name = name
        self.entity_type = entity_type
        self.hp = hp
        self.armor_class = armor_class
        self.position = (0, 0)
        self.personality = None


def _make_state(current="Fighter"):
    fighter = EntitySnapshot(
        name="Fighter", entity_type="player", hp=20, max_hp=20,
        armor_class=16, position=(0, 0), conditions=(), stats={},
        speed=30, faction="player", is_alive=True,
    )
    goblin = EntitySnapshot(
        name="Goblin", entity_type="enemy", hp=7, max_hp=7,
        armor_class=13, position=(1, 0), conditions=(), stats={},
        speed=30, faction="enemy", is_alive=True,
    )
    return GameState(
        round_number=1, current_entity_name=current,
        entities=(fighter, goblin), initiative_order=("Fighter", "Goblin"),
        world_width=5, world_height=5, tile_type="square",
    )


# ── Tests ────────────────────────────────────────────────────────────────


class TestCLIAdapterChooseAction:

    def test_choose_attack(self):
        """Selecting ATTACK prompts for target and returns AttackAction."""
        fighter = SimpleEntity("Fighter")
        goblin = SimpleEntity("Goblin", entity_type="enemy", hp=7)
        adapter = CLIAdapter(entities_by_name={"Fighter": fighter, "Goblin": goblin})
        state = _make_state()

        # User picks action "1" (ATTACK), then target "1" (Goblin)
        with patch("builtins.input", side_effect=["1", "1"]):
            action = adapter.choose_action("Fighter", state, ["ATTACK", "END_TURN"])

        assert isinstance(action, AttackAction)

    def test_choose_end_turn(self):
        """Selecting END_TURN returns EndTurnAction."""
        fighter = SimpleEntity("Fighter")
        adapter = CLIAdapter(entities_by_name={"Fighter": fighter})
        state = _make_state()

        with patch("builtins.input", side_effect=["2"]):
            action = adapter.choose_action("Fighter", state, ["ATTACK", "END_TURN"])

        assert isinstance(action, EndTurnAction)

    def test_choose_move(self):
        """Selecting MOVE prompts for position and returns MoveAction."""
        fighter = SimpleEntity("Fighter")
        adapter = CLIAdapter(entities_by_name={"Fighter": fighter})
        state = _make_state()

        with patch("builtins.input", side_effect=["1", "3,2"]):
            action = adapter.choose_action("Fighter", state, ["MOVE", "END_TURN"])

        assert isinstance(action, MoveAction)

    def test_invalid_then_valid_input(self):
        """Invalid action number retries until valid."""
        fighter = SimpleEntity("Fighter")
        adapter = CLIAdapter(entities_by_name={"Fighter": fighter})
        state = _make_state()

        with patch("builtins.input", side_effect=["0", "abc", "99", "1"]):
            action = adapter.choose_action("Fighter", state, ["END_TURN"])

        assert isinstance(action, EndTurnAction)

    def test_attack_no_targets_falls_back(self):
        """ATTACK with no living enemies falls back to EndTurnAction."""
        fighter = SimpleEntity("Fighter")
        adapter = CLIAdapter(entities_by_name={"Fighter": fighter})
        # All enemies dead
        dead_goblin = EntitySnapshot(
            name="Goblin", entity_type="enemy", hp=0, max_hp=7,
            armor_class=13, position=(1, 0), conditions=(), stats={},
            speed=30, faction="enemy", is_alive=False,
        )
        state = GameState(
            round_number=1, current_entity_name="Fighter",
            entities=(
                EntitySnapshot(
                    name="Fighter", entity_type="player", hp=20, max_hp=20,
                    armor_class=16, position=(0, 0), conditions=(), stats={},
                    speed=30, faction="player", is_alive=True,
                ),
                dead_goblin,
            ),
            initiative_order=("Fighter", "Goblin"),
            world_width=5, world_height=5, tile_type="square",
        )

        with patch("builtins.input", side_effect=["1"]):
            action = adapter.choose_action("Fighter", state, ["ATTACK", "END_TURN"])

        assert isinstance(action, EndTurnAction)

    def test_unknown_entity_uses_stub(self):
        """CLIAdapter creates a stub when entity is not in entities_by_name."""
        adapter = CLIAdapter(entities_by_name={})
        state = _make_state()

        with patch("builtins.input", side_effect=["1"]):
            action = adapter.choose_action("Fighter", state, ["END_TURN"])

        assert isinstance(action, EndTurnAction)


class TestCLIAdapterChooseTarget:

    def test_valid_target_selection(self):
        """Selecting a valid target number returns the target name."""
        adapter = CLIAdapter()
        state = _make_state()

        with patch("builtins.input", side_effect=["1"]):
            target = adapter.choose_target("Fighter", state, ["Goblin"])

        assert target == "Goblin"

    def test_invalid_then_valid_target(self):
        """Invalid target number retries."""
        adapter = CLIAdapter()
        state = _make_state()

        with patch("builtins.input", side_effect=["0", "abc", "1"]):
            target = adapter.choose_target("Fighter", state, ["Goblin"])

        assert target == "Goblin"


class TestCLIAdapterChooseMovement:

    def test_valid_position(self):
        """Entering x,y returns the position tuple."""
        adapter = CLIAdapter()
        state = _make_state()

        with patch("builtins.input", side_effect=["3,4"]):
            pos = adapter.choose_movement("Fighter", state, [])

        assert pos == (3, 4)

    def test_position_with_spaces(self):
        """Handles spaces in the input."""
        adapter = CLIAdapter()
        state = _make_state()

        with patch("builtins.input", side_effect=["  2 , 1  "]):
            pos = adapter.choose_movement("Fighter", state, [])

        assert pos == (2, 1)

    def test_invalid_then_valid_position(self):
        """Invalid formats retry."""
        adapter = CLIAdapter()
        state = _make_state()

        with patch("builtins.input", side_effect=["abc", "1", "2,3"]):
            pos = adapter.choose_movement("Fighter", state, [])

        assert pos == (2, 3)

    def test_constrained_positions(self):
        """When valid_positions list is given, rejects positions not in it."""
        adapter = CLIAdapter()
        state = _make_state()

        with patch("builtins.input", side_effect=["9,9", "1,0"]):
            pos = adapter.choose_movement("Fighter", state, [(0, 0), (1, 0), (0, 1)])

        assert pos == (1, 0)


class TestCLIAdapterDisplay:

    def test_display_state_prints_info(self, capsys):
        """_display_state prints entity info and enemies."""
        adapter = CLIAdapter()
        state = _make_state()
        adapter._display_state(state, "Fighter")

        captured = capsys.readouterr()
        assert "Fighter" in captured.out
        assert "Round 1" in captured.out
        assert "Goblin" in captured.out

    def test_display_state_missing_entity(self, capsys):
        """_display_state returns early for unknown entity."""
        adapter = CLIAdapter()
        state = _make_state()
        adapter._display_state(state, "NonExistent")

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_display_actions_lists_options(self, capsys):
        """_display_actions prints numbered action list."""
        adapter = CLIAdapter()
        adapter._display_actions(["ATTACK", "MOVE", "END_TURN"])

        captured = capsys.readouterr()
        assert "1. ATTACK" in captured.out
        assert "2. MOVE" in captured.out
        assert "3. END_TURN" in captured.out

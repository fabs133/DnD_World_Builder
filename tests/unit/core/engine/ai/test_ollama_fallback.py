"""Tests for AIAdapter fallback to HeuristicAIAdapter on connection failure."""

import logging

import pytest
from unittest.mock import MagicMock
import requests

from core.engine.ai.ai_adapter import AIAdapter
from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
from core.engine.ai.ollama_client import OllamaClient
from core.engine.game_state import GameState, EntitySnapshot
from core.engine.actions.attack_action import AttackAction
from core.engine.actions.move_action import MoveAction
from core.engine.actions.end_turn_action import EndTurnAction


class SimpleEntity:
    def __init__(self, name, entity_type="enemy", hp=10, max_hp=10,
                 armor_class=12, position=(0, 0)):
        self.name = name
        self.entity_type = entity_type
        self.hp = hp
        self.max_hp = max_hp
        self.armor_class = armor_class
        self.position = position
        self.personality = None
        self.conditions = []
        self.stats = {"Dexterity": 10, "max_hp": max_hp}
        self.speed = 30
        self.triggers = []
        self.inventory = []


def _make_state():
    """State with an adjacent enemy so the heuristic will choose to attack."""
    goblin = EntitySnapshot(
        name="Goblin", entity_type="enemy", hp=7, max_hp=7,
        armor_class=13, position=(1, 0), conditions=(), stats={},
        speed=30, faction="enemy", is_alive=True,
    )
    fighter = EntitySnapshot(
        name="Fighter", entity_type="player", hp=20, max_hp=20,
        armor_class=16, position=(0, 0), conditions=(), stats={},
        speed=30, faction="player", is_alive=True,
    )
    return GameState(
        round_number=1, current_entity_name="Goblin",
        entities=(goblin, fighter),
        initiative_order=("Goblin", "Fighter"),
        world_width=5, world_height=5, tile_type="square",
    )


class TestOllamaFallback:
    """When Ollama is unreachable, AIAdapter switches to HeuristicAIAdapter."""

    def test_falls_back_on_connection_error(self):
        mock_client = MagicMock(spec=OllamaClient)
        mock_client.generate.side_effect = ConnectionError("Connection refused")

        goblin = SimpleEntity("Goblin", "enemy", hp=7, max_hp=7, position=(1, 0))
        fighter = SimpleEntity("Fighter", "player", hp=20, max_hp=20, position=(0, 0))

        adapter = AIAdapter(
            ollama_client=mock_client,
            entities_by_name={"Goblin": goblin, "Fighter": fighter},
        )

        state = _make_state()
        action = adapter.choose_action("Goblin", state, ["ATTACK", "MOVE", "END_TURN"])

        # Should get a real action from heuristic, not EndTurnAction
        assert isinstance(action, AttackAction)
        # Only one attempt — switches immediately on connection error
        assert mock_client.generate.call_count == 1

    def test_falls_back_on_requests_connection_error(self):
        mock_client = MagicMock(spec=OllamaClient)
        mock_client.generate.side_effect = requests.ConnectionError("unreachable")

        goblin = SimpleEntity("Goblin", "enemy", hp=7, max_hp=7, position=(1, 0))
        fighter = SimpleEntity("Fighter", "player", hp=20, max_hp=20, position=(0, 0))

        adapter = AIAdapter(
            ollama_client=mock_client,
            entities_by_name={"Goblin": goblin, "Fighter": fighter},
        )

        state = _make_state()
        action = adapter.choose_action("Goblin", state, ["ATTACK", "MOVE", "END_TURN"])

        assert isinstance(action, AttackAction)
        assert mock_client.generate.call_count == 1

    def test_falls_back_on_timeout(self):
        mock_client = MagicMock(spec=OllamaClient)
        mock_client.generate.side_effect = requests.Timeout("timed out")

        goblin = SimpleEntity("Goblin", "enemy", hp=7, max_hp=7, position=(1, 0))
        fighter = SimpleEntity("Fighter", "player", hp=20, max_hp=20, position=(0, 0))

        adapter = AIAdapter(
            ollama_client=mock_client,
            entities_by_name={"Goblin": goblin, "Fighter": fighter},
        )

        state = _make_state()
        action = adapter.choose_action("Goblin", state, ["ATTACK", "MOVE", "END_TURN"])

        assert isinstance(action, AttackAction)

    def test_fallback_logged_as_warning(self, caplog):
        mock_client = MagicMock(spec=OllamaClient)
        mock_client.generate.side_effect = ConnectionError("refused")

        goblin = SimpleEntity("Goblin", "enemy", hp=7, max_hp=7, position=(1, 0))
        fighter = SimpleEntity("Fighter", "player", hp=20, max_hp=20, position=(0, 0))

        adapter = AIAdapter(
            ollama_client=mock_client,
            entities_by_name={"Goblin": goblin, "Fighter": fighter},
        )

        state = _make_state()
        with caplog.at_level(logging.WARNING):
            adapter.choose_action("Goblin", state, ["ATTACK", "MOVE", "END_TURN"])

        assert any("Ollama unreachable" in r.message for r in caplog.records)
        assert any(r.levelno == logging.WARNING for r in caplog.records
                   if "Ollama unreachable" in r.message)

    def test_subsequent_calls_skip_ollama(self):
        """After first connection failure, all future calls go to heuristic."""
        mock_client = MagicMock(spec=OllamaClient)
        mock_client.generate.side_effect = ConnectionError("refused")

        goblin = SimpleEntity("Goblin", "enemy", hp=7, max_hp=7, position=(1, 0))
        fighter = SimpleEntity("Fighter", "player", hp=20, max_hp=20, position=(0, 0))

        adapter = AIAdapter(
            ollama_client=mock_client,
            entities_by_name={"Goblin": goblin, "Fighter": fighter},
        )

        state = _make_state()

        # First call triggers fallback
        adapter.choose_action("Goblin", state, ["ATTACK", "MOVE", "END_TURN"])
        assert mock_client.generate.call_count == 1

        # Second call should NOT call Ollama at all
        adapter.choose_action("Goblin", state, ["ATTACK", "MOVE", "END_TURN"])
        assert mock_client.generate.call_count == 1  # Still 1 — no new calls

    def test_parse_errors_still_retry(self):
        """Parse errors (not connection errors) should still retry normally."""
        mock_client = MagicMock(spec=OllamaClient)
        mock_client.generate.side_effect = [
            "garbage",            # parse error → retry
            "ACTION: END_TURN",   # success
        ]

        adapter = AIAdapter(
            ollama_client=mock_client,
            entities_by_name={"Goblin": SimpleEntity("Goblin")},
        )

        state = _make_state()
        action = adapter.choose_action("Goblin", state, ["END_TURN"])

        assert isinstance(action, EndTurnAction)
        assert mock_client.generate.call_count == 2
        assert not adapter._using_fallback  # Should NOT have switched to fallback

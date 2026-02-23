"""Tests for AIAdapter with mocked Ollama."""

import pytest
from unittest.mock import MagicMock, patch
from core.engine.ai.ai_adapter import AIAdapter
from core.engine.ai.ollama_client import OllamaClient
from core.engine.ai import TACTICAL
from core.engine.game_state import GameState, EntitySnapshot
from core.engine.actions.attack_action import AttackAction
from core.engine.actions.end_turn_action import EndTurnAction


class SimpleEntity:
    def __init__(self, name, hp=10, armor_class=12):
        self.name = name
        self.hp = hp
        self.armor_class = armor_class
        self.entity_type = "enemy"
        self.position = (0, 0)
        self.personality = None


def _make_state():
    fighter = EntitySnapshot(
        name="Fighter", entity_type="player", hp=20, max_hp=20,
        armor_class=16, position=(0, 0), conditions=(), stats={},
        speed=30, faction="player", is_alive=True,
    )
    goblin = EntitySnapshot(
        name="Goblin", entity_type="enemy", hp=7, max_hp=7,
        armor_class=13, position=(2, 0), conditions=(), stats={},
        speed=30, faction="enemy", is_alive=True,
    )
    return GameState(
        round_number=1, current_entity_name="Goblin",
        entities=(fighter, goblin), initiative_order=("Fighter", "Goblin"),
        world_width=5, world_height=5, tile_type="square",
    )


class TestAIAdapter:
    def test_successful_attack_parse(self):
        mock_client = MagicMock(spec=OllamaClient)
        mock_client.generate.return_value = "ACTION: ATTACK TARGET: Fighter"

        fighter = SimpleEntity("Fighter")
        fighter.entity_type = "player"
        adapter = AIAdapter(
            ollama_client=mock_client,
            entities_by_name={"Fighter": fighter, "Goblin": SimpleEntity("Goblin")},
        )

        state = _make_state()
        action = adapter.choose_action("Goblin", state, ["ATTACK", "END_TURN"])

        assert isinstance(action, AttackAction)
        mock_client.generate.assert_called_once()

    def test_successful_end_turn(self):
        mock_client = MagicMock(spec=OllamaClient)
        mock_client.generate.return_value = "ACTION: END_TURN"

        adapter = AIAdapter(
            ollama_client=mock_client,
            entities_by_name={"Goblin": SimpleEntity("Goblin")},
        )

        state = _make_state()
        action = adapter.choose_action("Goblin", state, ["END_TURN"])
        assert isinstance(action, EndTurnAction)

    def test_retry_on_parse_error(self):
        mock_client = MagicMock(spec=OllamaClient)
        mock_client.generate.side_effect = [
            "I'm not sure what to do",  # bad parse
            "ACTION: END_TURN",  # good parse
        ]

        adapter = AIAdapter(
            ollama_client=mock_client,
            entities_by_name={"Goblin": SimpleEntity("Goblin")},
        )

        state = _make_state()
        action = adapter.choose_action("Goblin", state, ["END_TURN"])

        assert isinstance(action, EndTurnAction)
        assert mock_client.generate.call_count == 2

    def test_fallback_to_end_turn_on_all_failures(self):
        mock_client = MagicMock(spec=OllamaClient)
        mock_client.generate.return_value = "garbage output"

        adapter = AIAdapter(
            ollama_client=mock_client,
            max_retries=3,
            entities_by_name={"Goblin": SimpleEntity("Goblin")},
        )

        state = _make_state()
        action = adapter.choose_action("Goblin", state, ["ATTACK"])

        # Should fall back to EndTurnAction after 3 failures
        assert isinstance(action, EndTurnAction)
        assert mock_client.generate.call_count == 3

    def test_fallback_on_connection_error(self):
        """ConnectionError now immediately switches to HeuristicAIAdapter."""
        mock_client = MagicMock(spec=OllamaClient)
        mock_client.generate.side_effect = ConnectionError("No Ollama")

        fighter = SimpleEntity("Fighter")
        fighter.entity_type = "player"
        fighter.position = (2, 0)

        adapter = AIAdapter(
            ollama_client=mock_client,
            max_retries=2,
            entities_by_name={
                "Goblin": SimpleEntity("Goblin"),
                "Fighter": fighter,
            },
        )

        state = _make_state()
        action = adapter.choose_action(
            "Goblin", state, ["ATTACK", "MOVE", "END_TURN"],
        )

        # Heuristic fallback produces a real action (move toward enemy)
        assert not isinstance(action, EndTurnAction)
        # Only one Ollama attempt before switching
        assert mock_client.generate.call_count == 1

"""Integration test for the demo encounter scenario."""

import pytest
from unittest.mock import MagicMock
from core.engine.scenarios.demo_encounter import build_demo_encounter, DemoEntity
from core.engine.input_adapter import TestAdapter
from core.engine.ai.ai_adapter import AIAdapter
from core.engine.ai.ollama_client import OllamaClient
from core.engine.ai import AGGRESSIVE
from core.engine.actions.attack_action import AttackAction
from core.engine.actions.end_turn_action import EndTurnAction

import random


class TestDemoEncounter:
    def _mock_adapters(self, entities_by_name):
        """Create AI adapters with mocked Ollama for testing."""
        adapters = {}
        for name in ("Fighter", "Ranger"):
            mock = MagicMock(spec=OllamaClient)
            # Players attack nearest goblin
            mock.generate.return_value = "ACTION: ATTACK TARGET: Goblin_1"
            adapters[name] = AIAdapter(
                ollama_client=mock,
                entities_by_name=entities_by_name,
            )
        return adapters

    def test_build_creates_valid_session(self):
        """The demo encounter builds without errors."""
        rng = random.Random(42)
        fighter = DemoEntity("Fighter", "player", hp=28)
        goblin = DemoEntity("Goblin_1", "enemy", hp=7)

        # Provide scripted player adapters to avoid real Ollama
        player_actions = [EndTurnAction(fighter) for _ in range(20)]
        player_adapters = {
            "Fighter": TestAdapter(action_sequence=player_actions),
            "Ranger": TestAdapter(action_sequence=player_actions.copy()),
        }

        session = build_demo_encounter(
            player_adapters=player_adapters, seed=42, max_rounds=3,
        )

        # Session should be creatable
        assert session is not None

    def test_demo_runs_with_mocked_ai(self):
        """Full demo encounter runs to completion with mocked Ollama."""
        session = build_demo_encounter(seed=42, max_rounds=10)

        # Replace all adapters with mocked ones
        entities_by_name = {e.name: e for e in session._gm.game_entities}

        for name in session._adapters:
            mock_client = MagicMock(spec=OllamaClient)
            if "Goblin" in name:
                mock_client.generate.return_value = "ACTION: ATTACK TARGET: Fighter"
            else:
                mock_client.generate.return_value = "ACTION: ATTACK TARGET: Goblin_1"

            session._adapters[name] = AIAdapter(
                ollama_client=mock_client,
                default_personality=AGGRESSIVE,
                entities_by_name=entities_by_name,
            )

        session.setup()
        result = session.run()

        assert result.rounds_played >= 1
        assert result.termination_reason != ""
        assert len(result.action_history) > 0

    def test_demo_deterministic(self):
        """Same seed produces same initiative order."""
        s1 = build_demo_encounter(seed=42)
        s2 = build_demo_encounter(seed=42)

        s1.setup()
        s2.setup()

        order1 = s1._initiative.get_order()
        order2 = s2._initiative.get_order()

        assert order1 == order2

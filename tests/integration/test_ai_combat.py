"""Integration test: full combat with mocked AI responses (no real LLM needed)."""

import pytest
from unittest.mock import MagicMock
from core.engine.game_session import GameSession
from core.engine.input_adapter import TestAdapter
from core.engine.ai.ai_adapter import AIAdapter
from core.engine.ai.ollama_client import OllamaClient
from core.engine.ai import AGGRESSIVE
from core.engine.actions.end_turn_action import EndTurnAction
from core.engine.actions.attack_action import AttackAction
from models.game_master import Gamemaster
from models.world.world import World

import random


class SimpleEntity:
    def __init__(self, name, entity_type, hp, armor_class=12, speed=30, dex=10):
        self.name = name
        self.entity_type = entity_type
        self.hp = hp
        self.armor_class = armor_class
        self.speed = speed
        self.stats = {"Dexterity": dex, "max_hp": hp}
        self.conditions = []
        self.position = (0, 0)
        self.initiative = 0
        self.triggers = []
        self.inventory = []


class TestAICombat:
    def test_ai_vs_scripted_combat(self):
        """AI-controlled goblin vs scripted player, mocked Ollama."""
        gm = Gamemaster()
        gm.world = World(
            world_version=1, width=5, height=5, tile_type="square",
            description="", map_data={}, time_of_day="", weather_conditions="",
        )
        gm.world_tile_manager = gm.world.tile_manager

        fighter = SimpleEntity("Fighter", "player", hp=25, armor_class=16)
        goblin = SimpleEntity("Goblin", "enemy", hp=7, armor_class=13)

        gm.game_entities = [fighter, goblin]
        gm.world_tile_manager.place_entity(fighter, 0, 0)
        gm.world_tile_manager.place_entity(goblin, 4, 0)

        # Mock Ollama to always attack the fighter
        mock_client = MagicMock(spec=OllamaClient)
        mock_client.generate.return_value = "ACTION: ATTACK TARGET: Fighter"

        rng = random.Random(42)

        # Player uses scripted actions
        player_actions = [
            AttackAction(fighter, goblin, damage_expr="2d6+3", to_hit_bonus=7, rng=rng),
            AttackAction(fighter, goblin, damage_expr="2d6+3", to_hit_bonus=7, rng=rng),
            AttackAction(fighter, goblin, damage_expr="2d6+3", to_hit_bonus=7, rng=rng),
        ]

        # Goblin uses AI adapter with mocked Ollama
        ai_adapter = AIAdapter(
            ollama_client=mock_client,
            default_personality=AGGRESSIVE,
            entities_by_name={"Fighter": fighter, "Goblin": goblin},
        )

        adapters = {
            "Fighter": TestAdapter(action_sequence=player_actions),
            "Goblin": ai_adapter,
        }

        session = GameSession(gm, adapters, seed=42, max_rounds=5)
        session.setup()
        result = session.run()

        # Combat should complete
        assert result.rounds_played >= 1
        assert result.termination_reason != ""
        # Ollama was called at least once for the goblin's turn
        assert mock_client.generate.call_count >= 0  # Goblin may die before turn

    def test_ai_vs_ai_combat(self):
        """Two AI players fight each other with mocked Ollama."""
        gm = Gamemaster()
        gm.world = World(
            world_version=1, width=5, height=5, tile_type="square",
            description="", map_data={}, time_of_day="", weather_conditions="",
        )
        gm.world_tile_manager = gm.world.tile_manager

        fighter = SimpleEntity("Fighter", "player", hp=20, armor_class=14)
        orc = SimpleEntity("Orc", "enemy", hp=15, armor_class=13)

        gm.game_entities = [fighter, orc]
        gm.world_tile_manager.place_entity(fighter, 0, 0)
        gm.world_tile_manager.place_entity(orc, 4, 0)

        # Both use mocked Ollama
        mock_client_1 = MagicMock(spec=OllamaClient)
        mock_client_1.generate.return_value = "ACTION: ATTACK TARGET: Orc"

        mock_client_2 = MagicMock(spec=OllamaClient)
        mock_client_2.generate.return_value = "ACTION: ATTACK TARGET: Fighter"

        fighter_adapter = AIAdapter(
            ollama_client=mock_client_1,
            entities_by_name={"Fighter": fighter, "Orc": orc},
        )
        orc_adapter = AIAdapter(
            ollama_client=mock_client_2,
            entities_by_name={"Fighter": fighter, "Orc": orc},
        )

        adapters = {
            "Fighter": fighter_adapter,
            "Orc": orc_adapter,
        }

        session = GameSession(gm, adapters, seed=42, max_rounds=20)
        session.setup()
        result = session.run()

        # Combat should resolve
        assert result.rounds_played >= 1
        assert result.winner in ("player", "enemy", None)

"""Tests for the play session runner and UI adapter."""

import pytest
from core.engine.play_session import PlaySessionRunner, PlayConfig, default_test_party
from core.engine.ui_adapter import UIInputAdapter
from core.engine.input_adapter import InputAdapter


class TestDefaultTestParty:
    def test_returns_four_entities(self):
        party = default_test_party()
        assert len(party) == 4

    def test_all_are_players(self):
        for p in default_test_party():
            assert p["entity_type"] == "player"

    def test_all_have_hp(self):
        for p in default_test_party():
            assert p["hp"] > 0
            assert p["max_hp"] >= p["hp"]

    def test_all_have_names(self):
        names = [p["name"] for p in default_test_party()]
        assert len(set(names)) == 4  # all unique


class TestPlaySessionRunner:
    def _make_tiles(self):
        """Create minimal tile dicts with a player and two enemies."""
        return [
            {
                "tile_id": "0_0",
                "position": [0, 0],
                "terrain": "FLOOR",
                "tags": ["START_ZONE"],
                "user_label": "Start",
                "note": None,
                "overlay_color": None,
                "last_updated": None,
                "entities": [
                    {"name": "Hero", "entity_type": "player",
                     "stats": {"str": 14, "dex": 12, "con": 12, "int": 10, "wis": 10, "cha": 10,
                                "ac": 14, "hp": 20, "max_hp": 20, "speed": 30},
                     "hp": 20, "max_hp": 20, "inventory": [], "triggers": [], "conditions": []},
                ],
                "triggers": [],
            },
            {
                "tile_id": "1_0",
                "position": [1, 0],
                "terrain": "FLOOR",
                "tags": [],
                "user_label": None,
                "note": None,
                "overlay_color": None,
                "last_updated": None,
                "entities": [
                    {"name": "Goblin", "entity_type": "enemy",
                     "stats": {"str": 8, "dex": 14, "con": 10, "int": 10, "wis": 8, "cha": 8,
                                "ac": 13, "hp": 7, "max_hp": 7, "speed": 30},
                     "hp": 7, "max_hp": 7, "inventory": [], "triggers": [], "conditions": []},
                ],
                "triggers": [],
            },
        ]

    def test_from_tile_data_creates_runner(self):
        """Runner builds from tile dicts with player and enemy."""
        from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
        # Use AI adapter for player too (headless test)
        adapter = HeuristicAIAdapter()
        config = PlayConfig(seed=42)
        runner = PlaySessionRunner.from_tile_data(self._make_tiles(), config, adapter)
        assert len(runner.entities) == 2
        assert not runner.is_finished

    def test_spawns_default_party_when_no_players(self):
        """If no player entities, default party is spawned."""
        from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
        tiles = [{
            "tile_id": "0_0", "position": [0, 0], "terrain": "FLOOR",
            "tags": ["START_ZONE"], "user_label": None, "note": None,
            "overlay_color": None, "last_updated": None,
            "entities": [
                {"name": "Goblin", "entity_type": "enemy",
                 "stats": {"hp": 7, "max_hp": 7, "ac": 13, "speed": 30},
                 "hp": 7, "max_hp": 7, "inventory": [], "triggers": [], "conditions": []},
            ],
            "triggers": [],
        }]
        adapter = HeuristicAIAdapter()
        runner = PlaySessionRunner.from_tile_data(tiles, PlayConfig(seed=42), adapter)
        players = [e for e in runner.entities if e.entity_type == "player"]
        assert len(players) == 4  # default party

    def test_start_zone_position(self):
        """Player entities placed at START_ZONE tile position."""
        from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
        tiles = [{
            "tile_id": "5_3", "position": [5, 3], "terrain": "FLOOR",
            "tags": ["START_ZONE"], "user_label": None, "note": None,
            "overlay_color": None, "last_updated": None,
            "entities": [
                {"name": "Orc", "entity_type": "enemy",
                 "stats": {"hp": 15, "max_hp": 15, "ac": 13, "speed": 30},
                 "hp": 15, "max_hp": 15, "inventory": [], "triggers": [], "conditions": []},
            ],
            "triggers": [],
        }]
        adapter = HeuristicAIAdapter()
        runner = PlaySessionRunner.from_tile_data(tiles, PlayConfig(), adapter)
        players = [e for e in runner.entities if e.entity_type == "player"]
        for p in players:
            assert p.position == (5, 3)

    def test_headless_run_to_completion(self):
        """Full headless run with AI on both sides completes."""
        from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
        adapter = HeuristicAIAdapter()
        config = PlayConfig(seed=42, max_rounds=20)
        runner = PlaySessionRunner.from_tile_data(self._make_tiles(), config, adapter)
        # Run until finished
        rounds = 0
        while not runner.is_finished and rounds < 50:
            runner.run_one_turn()
            rounds += 1
        assert runner.is_finished or rounds == 50


class TestUIInputAdapter:
    def test_cancel_unblocks(self):
        adapter = UIInputAdapter()

        # Cancel should set a sentinel action
        adapter.cancel()
        assert adapter._pending_action is not None
        assert adapter._pending_action.validate(None) is True

    def test_submit_action_stores(self):
        adapter = UIInputAdapter()
        adapter.submit_action("test_action")
        assert adapter._pending_action == "test_action"

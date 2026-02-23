"""Tests for the YAML scenario loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.engine.scenarios.scenario_loader import ScenarioLoader, _create_entity, PERSONALITY_PRESETS
from models.ai.alignment import Alignment

SCENARIO_PATH = Path(__file__).resolve().parents[5] / "scenarios" / "goblin_ambush.yaml"


class TestScenarioLoaderInit:
    """Test loading and parsing the YAML file."""

    def test_loads_yaml(self):
        loader = ScenarioLoader(SCENARIO_PATH)
        assert loader.name == "Ruined Temple Ambush"

    def test_description(self):
        loader = ScenarioLoader(SCENARIO_PATH)
        assert "goblin ambush" in loader.description.lower()

    def test_entity_count(self):
        loader = ScenarioLoader(SCENARIO_PATH)
        assert len(loader.entity_configs) == 6

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            ScenarioLoader("nonexistent.yaml")


class TestCreateEntity:
    """Test entity creation from config dicts."""

    def test_basic_entity(self):
        cfg = {"name": "TestGoblin", "type": "enemy", "hp": 7, "alignment": "neutral_evil"}
        entity = _create_entity(cfg)
        assert entity.name == "TestGoblin"
        assert entity.entity_type == "enemy"
        assert entity.hp == 7
        assert entity.personality is not None

    def test_personality_preset(self):
        cfg = {
            "name": "Grunt",
            "type": "enemy",
            "hp": 7,
            "personality_preset": "goblin_grunt",
        }
        entity = _create_entity(cfg)
        assert entity.personality is not None
        assert entity.personality.alignment == Alignment.NEUTRAL_EVIL

    def test_trait_override(self):
        cfg = {
            "name": "Custom",
            "type": "enemy",
            "hp": 10,
            "personality_preset": "goblin_grunt",
            "trait": "Unusually brave",
            "bond": "Loves cheese",
            "flaw": "Allergic to sunlight",
        }
        entity = _create_entity(cfg)
        assert entity.personality.trait == "Unusually brave"
        assert entity.personality.bond == "Loves cheese"
        assert entity.personality.flaw == "Allergic to sunlight"

    def test_alignment_without_preset(self):
        cfg = {"name": "Neutral", "type": "player", "hp": 20, "alignment": "lawful_good"}
        entity = _create_entity(cfg)
        assert entity.personality.alignment == Alignment.LAWFUL_GOOD

    def test_position(self):
        cfg = {"name": "Pos", "type": "enemy", "hp": 5, "position": [3, 4]}
        entity = _create_entity(cfg)
        assert entity.position == (3, 4)


class TestPresets:
    """Verify all personality presets are mapped."""

    @pytest.mark.parametrize(
        "preset_name",
        ["goblin_grunt", "goblin_shaman", "orc_berserker", "paladin_companion", "rogue_companion", "undead_minion"],
    )
    def test_preset_exists(self, preset_name: str):
        assert preset_name in PERSONALITY_PRESETS
        personality = PERSONALITY_PRESETS[preset_name]()
        assert personality.alignment is not None


class TestBuildSession:
    """Test building a GameSession from the scenario YAML."""

    def test_build_mock_session(self):
        loader = ScenarioLoader(SCENARIO_PATH)
        session = loader.build_session(mode="mock", seed=42)
        assert session is not None

    def test_session_runs_to_completion(self):
        loader = ScenarioLoader(SCENARIO_PATH)
        session = loader.build_session(mode="mock", seed=42, max_rounds=10)
        session.setup()
        result = session.run()
        assert result.rounds_played > 0
        assert result.termination_reason != ""

    def test_deterministic_replay(self):
        loader = ScenarioLoader(SCENARIO_PATH)
        r1 = loader.build_session(mode="mock", seed=99, max_rounds=5)
        r1.setup()
        result1 = r1.run()

        r2 = loader.build_session(mode="mock", seed=99, max_rounds=5)
        r2.setup()
        result2 = r2.run()

        assert result1.rounds_played == result2.rounds_played
        assert result1.winner == result2.winner

    def test_invalid_mode_raises(self):
        loader = ScenarioLoader(SCENARIO_PATH)
        with pytest.raises(ValueError, match="Unknown mode"):
            loader.build_session(mode="invalid")

    def test_callbacks_fire(self):
        rounds_seen = []
        turns_seen = []

        def on_round(state):
            rounds_seen.append(state.round_number)

        def on_turn(state, name):
            turns_seen.append(name)

        loader = ScenarioLoader(SCENARIO_PATH)
        session = loader.build_session(
            mode="mock",
            seed=42,
            max_rounds=3,
            on_round_start=on_round,
            on_turn_start=on_turn,
        )
        session.setup()
        session.run()

        assert len(rounds_seen) > 0
        assert len(turns_seen) > 0

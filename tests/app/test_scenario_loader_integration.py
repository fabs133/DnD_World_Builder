"""Scenario loader integration tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from core.engine.scenarios.scenario_loader import ScenarioLoader
from core.testing import ScenarioConfig, HarnessConfig, BehavioralTestHarness


class TestCustomScenarioYaml:
    def test_custom_scenario_loads_and_runs(self, tmp_path):
        """Create a temp YAML scenario, load, and run it."""
        scenario = {
            "name": "Custom Test",
            "description": "A custom test scenario",
            "map_size": [4, 4],
            "max_rounds": 5,
            "entities": [
                {
                    "name": "Hero",
                    "type": "player",
                    "hp": 20,
                    "armor_class": 14,
                    "dex": 12,
                    "speed": 30,
                    "position": [0, 0],
                    "alignment": "lawful_good",
                },
                {
                    "name": "Villain",
                    "type": "enemy",
                    "hp": 15,
                    "armor_class": 12,
                    "dex": 10,
                    "speed": 30,
                    "position": [3, 3],
                    "alignment": "chaotic_evil",
                },
            ],
        }
        yaml_path = tmp_path / "custom.yaml"
        yaml_path.write_text(yaml.dump(scenario))

        loader = ScenarioLoader(str(yaml_path))
        session = loader.build_session(mode="mock", seed=1, max_rounds=5)
        session.setup()
        result = session.run()
        assert result.rounds_played > 0


class TestMinimalScenario:
    def test_two_entities_small_map(self):
        """Minimal scenario: 2 entities on a 2x2 map."""
        config = ScenarioConfig(
            name="Minimal",
            entities=[
                {"name": "A", "type": "player", "hp": 10, "armor_class": 10,
                 "dex": 10, "speed": 30, "position": [0, 0], "alignment": "true_neutral"},
                {"name": "B", "type": "enemy", "hp": 10, "armor_class": 10,
                 "dex": 10, "speed": 30, "position": [1, 1], "alignment": "true_neutral"},
            ],
            map_size=(2, 2),
            max_rounds=5,
        )
        harness = BehavioralTestHarness(config, HarnessConfig(runs=2, seed_start=1, parallel_workers=1))
        result = harness.run()
        assert result.successful_runs == 2


class TestAllPresetsLoad:
    """Verify all personality presets can be used in scenarios."""

    @pytest.mark.parametrize("preset", [
        "goblin_grunt",
        "goblin_shaman",
        "orc_berserker",
        "paladin_companion",
        "rogue_companion",
        "undead_minion",
    ])
    def test_preset_creates_entity(self, preset):
        config = ScenarioConfig(
            name=f"Preset: {preset}",
            entities=[
                {"name": "Player", "type": "player", "hp": 20, "armor_class": 14,
                 "dex": 12, "speed": 30, "position": [0, 0], "alignment": "lawful_good"},
                {"name": "Test_Entity", "type": "enemy", "hp": 10, "armor_class": 12,
                 "dex": 10, "speed": 30, "position": [4, 4], "alignment": "neutral_evil",
                 "personality_preset": preset},
            ],
            map_size=(5, 5),
            max_rounds=5,
        )
        harness = BehavioralTestHarness(config, HarnessConfig(runs=1, seed_start=1, parallel_workers=1))
        result = harness.run()
        assert result.successful_runs == 1


class TestGoblinAmbushLoads:
    def test_goblin_ambush_loads(self, goblin_ambush_yaml):
        """The bundled goblin ambush YAML loads successfully."""
        loader = ScenarioLoader(str(goblin_ambush_yaml))
        assert loader.name is not None
        assert len(loader.entity_configs) > 0

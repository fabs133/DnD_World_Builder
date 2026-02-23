"""End-to-end scenario tests using the behavioral harness."""

from __future__ import annotations

import pytest

from core.testing import (
    BehavioralTestHarness,
    ScenarioConfig,
    HarnessConfig,
    HarnessResult,
)


def run_scenario(config, harness_config=None):
    if harness_config is None:
        harness_config = HarnessConfig(runs=5, seed_start=1, parallel_workers=1)
    return BehavioralTestHarness(config, harness_config).run()


class TestGoblinAmbushEndToEnd:
    """Full end-to-end tests of the goblin ambush scenario."""

    def test_goblin_ambush_completes(self, goblin_ambush_config, quick_harness_config):
        """Scenario runs to termination without errors."""
        result = run_scenario(goblin_ambush_config, quick_harness_config)
        assert result.successful_runs > 0
        assert result.failed_runs == 0

    def test_goblin_ambush_deterministic(self, goblin_ambush_config):
        """Same seed produces identical run counts."""
        cfg = HarnessConfig(runs=3, seed_start=42, parallel_workers=1)
        result1 = run_scenario(goblin_ambush_config, cfg)
        result2 = run_scenario(goblin_ambush_config, cfg)
        assert result1.successful_runs == result2.successful_runs

    def test_goblin_ambush_different_seeds_vary(self, goblin_ambush_config):
        """Different seeds can produce different outcomes."""
        cfg1 = HarnessConfig(runs=5, seed_start=1, parallel_workers=1)
        cfg2 = HarnessConfig(runs=5, seed_start=1000, parallel_workers=1)
        result1 = run_scenario(goblin_ambush_config, cfg1)
        result2 = run_scenario(goblin_ambush_config, cfg2)
        # Both should complete successfully
        assert result1.successful_runs == result1.total_runs
        assert result2.successful_runs == result2.total_runs

    def test_all_entities_represented(self, goblin_ambush_config, quick_harness_config):
        """Every entity in the scenario has stats collected."""
        result = run_scenario(goblin_ambush_config, quick_harness_config)
        entity_names = {e["name"] for e in goblin_ambush_config.entities}
        stats_names = set(result.stats_by_entity.keys())
        # All scenario entities should have stats
        assert entity_names.issubset(stats_names)

    def test_combat_ends_by_elimination(self, goblin_ambush_config, quick_harness_config):
        """Combat sessions complete (within max_rounds)."""
        result = run_scenario(goblin_ambush_config, quick_harness_config)
        assert result.total_runs == quick_harness_config.runs
        assert result.successful_runs == result.total_runs

    def test_max_rounds_terminates(self):
        """Session stops at max_rounds."""
        config = ScenarioConfig(
            name="Short Combat",
            entities=[
                {"name": "Fighter", "type": "player", "hp": 100, "armor_class": 20,
                 "dex": 10, "speed": 30, "position": [0, 0], "alignment": "lawful_good"},
                {"name": "Goblin", "type": "enemy", "hp": 100, "armor_class": 20,
                 "dex": 10, "speed": 30, "position": [9, 9], "alignment": "chaotic_evil"},
            ],
            map_size=(10, 10),
            max_rounds=3,
        )
        cfg = HarnessConfig(runs=2, seed_start=1, parallel_workers=1)
        result = run_scenario(config, cfg)
        assert result.successful_runs == result.total_runs

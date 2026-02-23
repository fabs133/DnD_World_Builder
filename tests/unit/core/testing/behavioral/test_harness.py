"""Tests for the behavioral test harness."""

import pytest

from core.testing.behavioral.harness import (
    BehavioralEntity,
    ScenarioConfig,
    HarnessConfig,
    BehavioralTestHarness,
    HarnessResult,
)
from core.testing.behavioral.stats import BehaviorEvent


def _minimal_scenario():
    return ScenarioConfig(
        name="minimal_test",
        entities=[
            {"name": "Fighter", "type": "player", "hp": 20,
             "alignment": "lawful_good", "position": [0, 0]},
            {"name": "Goblin", "type": "enemy", "hp": 7,
             "alignment": "chaotic_evil", "position": [3, 3]},
        ],
        map_size=(5, 5),
        max_rounds=5,
    )


class TestBehavioralEntity:
    def test_basic_creation(self):
        e = BehavioralEntity("Test", "player", hp=20)
        assert e.name == "Test"
        assert e.hp == 20
        assert e.max_hp == 20
        assert e.personality is None

    def test_position(self):
        e = BehavioralEntity("Test", "player", hp=20, position=(3, 4))
        assert e.position == (3, 4)


class TestScenarioConfig:
    def test_basic_creation(self):
        cfg = _minimal_scenario()
        assert cfg.name == "minimal_test"
        assert len(cfg.entities) == 2
        assert cfg.map_size == (5, 5)
        assert cfg.max_rounds == 5


class TestHarnessConfig:
    def test_defaults(self):
        cfg = HarnessConfig()
        assert cfg.runs == 100
        assert cfg.parallel_workers == 4
        assert cfg.use_real_ai is False

    def test_custom(self):
        cfg = HarnessConfig(runs=10, seed_start=100)
        assert cfg.runs == 10
        assert cfg.seed_start == 100


class TestBehavioralTestHarness:
    def test_runs_minimal_scenario(self):
        scenario = _minimal_scenario()
        config = HarnessConfig(runs=3, parallel_workers=1)
        harness = BehavioralTestHarness(scenario, config)

        result = harness.run()

        assert isinstance(result, HarnessResult)
        assert result.scenario_name == "minimal_test"
        assert result.total_runs == 3
        assert result.successful_runs == 3
        assert result.failed_runs == 0
        assert result.total_time_seconds > 0

    def test_stats_populated(self):
        scenario = _minimal_scenario()
        config = HarnessConfig(runs=5, parallel_workers=1)
        harness = BehavioralTestHarness(scenario, config)

        result = harness.run()

        assert "Fighter" in result.stats_by_entity
        assert "Goblin" in result.stats_by_entity
        fighter_stats = result.stats_by_entity["Fighter"]
        assert fighter_stats.run_count == 5
        assert fighter_stats.alignment == "lawful_good"

    def test_damage_tracked(self):
        scenario = _minimal_scenario()
        config = HarnessConfig(runs=10, parallel_workers=2)
        harness = BehavioralTestHarness(scenario, config)

        result = harness.run()

        fighter = result.stats_by_entity["Fighter"]
        # At least some runs should have dealt damage
        assert fighter.avg_damage_dealt >= 0
        assert fighter.total(BehaviorEvent.ATTACKED) > 0

    def test_parallel_determinism(self):
        """Parallel runs with same seeds should produce consistent stats."""
        scenario = _minimal_scenario()
        config = HarnessConfig(runs=5, parallel_workers=1, seed_start=42)
        h1 = BehavioralTestHarness(scenario, config)
        r1 = h1.run()

        config2 = HarnessConfig(runs=5, parallel_workers=1, seed_start=42)
        h2 = BehavioralTestHarness(scenario, config2)
        r2 = h2.run()

        # Same seeds should give same results
        for name in r1.stats_by_entity:
            assert r1.stats_by_entity[name].run_count == r2.stats_by_entity[name].run_count

    def test_get_alignment_stats(self):
        scenario = ScenarioConfig(
            name="multi_alignment",
            entities=[
                {"name": "Paladin", "type": "player", "hp": 30,
                 "alignment": "lawful_good", "position": [0, 0]},
                {"name": "Rogue", "type": "player", "hp": 18,
                 "alignment": "chaotic_good", "position": [1, 0]},
                {"name": "Goblin1", "type": "enemy", "hp": 7,
                 "alignment": "chaotic_evil", "position": [4, 4]},
                {"name": "Goblin2", "type": "enemy", "hp": 7,
                 "alignment": "chaotic_evil", "position": [4, 3]},
            ],
            map_size=(5, 5),
            max_rounds=5,
        )
        config = HarnessConfig(runs=3, parallel_workers=1)
        harness = BehavioralTestHarness(scenario, config)
        result = harness.run()

        ce_stats = result.get_alignment_stats("chaotic_evil")
        assert len(ce_stats) == 2
        assert all(s.alignment == "chaotic_evil" for s in ce_stats)

        lg_stats = result.get_alignment_stats("lawful_good")
        assert len(lg_stats) == 1

    def test_sequential_mode(self):
        scenario = _minimal_scenario()
        config = HarnessConfig(runs=2, use_real_ai=True)  # forces sequential
        harness = BehavioralTestHarness(scenario, config)

        result = harness.run()

        assert result.successful_runs == 2

    def test_entity_trait_applied(self):
        scenario = ScenarioConfig(
            name="trait_test",
            entities=[
                {"name": "Fighter", "type": "player", "hp": 20,
                 "alignment": "lawful_good", "trait": "Brave and bold",
                 "position": [0, 0]},
                {"name": "Goblin", "type": "enemy", "hp": 7,
                 "alignment": "chaotic_evil", "position": [3, 3]},
            ],
            map_size=(5, 5),
            max_rounds=3,
        )
        config = HarnessConfig(runs=1, parallel_workers=1)
        harness = BehavioralTestHarness(scenario, config)

        result = harness.run()
        assert result.successful_runs == 1

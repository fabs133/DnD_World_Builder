"""Performance benchmark tests."""

from __future__ import annotations

import time

import pytest

from core.testing import (
    BehavioralTestHarness,
    ScenarioConfig,
    HarnessConfig,
    MockAIAdapter,
    BehavioralEntity,
)
from core.engine.game_state import GameState, EntitySnapshot


class TestBatchPerformance:
    def test_100_runs_under_30_seconds(self):
        """BehavioralTestHarness with 100 runs completes in reasonable time."""
        config = ScenarioConfig(
            name="Performance Test",
            entities=[
                {"name": "Fighter", "type": "player", "hp": 20, "armor_class": 14,
                 "dex": 12, "speed": 30, "position": [0, 0], "alignment": "lawful_good"},
                {"name": "Goblin_1", "type": "enemy", "hp": 7, "armor_class": 13,
                 "dex": 14, "speed": 30, "position": [4, 1], "alignment": "neutral_evil"},
                {"name": "Goblin_2", "type": "enemy", "hp": 7, "armor_class": 13,
                 "dex": 14, "speed": 30, "position": [4, 3], "alignment": "neutral_evil"},
            ],
            map_size=(5, 5),
            max_rounds=10,
        )
        harness_config = HarnessConfig(
            runs=100,
            seed_start=1,
            parallel_workers=1,
            use_real_ai=False,
        )
        start = time.monotonic()
        result = BehavioralTestHarness(config, harness_config).run()
        elapsed = time.monotonic() - start

        assert result.successful_runs == 100
        assert elapsed < 30, f"100 runs took {elapsed:.1f}s (expected < 30s)"

    def test_runs_per_second_metric(self):
        """Verify runs_per_second is calculated."""
        config = ScenarioConfig(
            name="Speed Test",
            entities=[
                {"name": "A", "type": "player", "hp": 10, "armor_class": 12,
                 "dex": 10, "speed": 30, "position": [0, 0], "alignment": "true_neutral"},
                {"name": "B", "type": "enemy", "hp": 10, "armor_class": 12,
                 "dex": 10, "speed": 30, "position": [4, 4], "alignment": "true_neutral"},
            ],
            map_size=(5, 5),
            max_rounds=5,
        )
        harness_config = HarnessConfig(runs=10, seed_start=1, parallel_workers=1)
        result = BehavioralTestHarness(config, harness_config).run()
        assert result.runs_per_second > 0


class TestLargeScenario:
    def test_many_entities(self):
        """10v10 entities, 20 rounds, completes without timeout."""
        entities = []
        for i in range(10):
            entities.append({
                "name": f"Player_{i}",
                "type": "player",
                "hp": 15,
                "armor_class": 13,
                "dex": 12,
                "speed": 30,
                "position": [i % 5, i // 5],
                "alignment": "lawful_good",
            })
        for i in range(10):
            entities.append({
                "name": f"Enemy_{i}",
                "type": "enemy",
                "hp": 10,
                "armor_class": 12,
                "dex": 10,
                "speed": 30,
                "position": [5 + i % 5, i // 5],
                "alignment": "chaotic_evil",
            })

        config = ScenarioConfig(
            name="Large Battle",
            entities=entities,
            map_size=(10, 10),
            max_rounds=20,
        )
        harness_config = HarnessConfig(runs=3, seed_start=1, parallel_workers=1)

        start = time.monotonic()
        result = BehavioralTestHarness(config, harness_config).run()
        elapsed = time.monotonic() - start

        assert result.successful_runs == 3
        assert elapsed < 60, f"Large scenario took {elapsed:.1f}s (expected < 60s)"

"""Behavioral correctness tests for alignment-based AI."""

from __future__ import annotations

import pytest

from core.testing import (
    BehavioralTestHarness,
    ScenarioConfig,
    HarnessConfig,
    HarnessResult,
    AlignmentAssertions,
)


def run_scenario(config, harness_config=None):
    if harness_config is None:
        harness_config = HarnessConfig(runs=5, seed_start=1, parallel_workers=1)
    return BehavioralTestHarness(config, harness_config).run()


def _duel_config(alignment_a: str, alignment_b: str) -> ScenarioConfig:
    """Create a 1v1 duel scenario config."""
    return ScenarioConfig(
        name=f"Duel: {alignment_a} vs {alignment_b}",
        entities=[
            {
                "name": "Entity_A",
                "type": "player",
                "hp": 20,
                "armor_class": 14,
                "dex": 12,
                "speed": 30,
                "position": [0, 0],
                "alignment": alignment_a,
            },
            {
                "name": "Entity_B",
                "type": "enemy",
                "hp": 20,
                "armor_class": 14,
                "dex": 12,
                "speed": 30,
                "position": [4, 4],
                "alignment": alignment_b,
            },
        ],
        map_size=(5, 5),
        max_rounds=20,
    )


def _multi_config(alignment: str) -> ScenarioConfig:
    """Create a 2v2 scenario to test ally interactions."""
    return ScenarioConfig(
        name=f"Team battle: {alignment}",
        entities=[
            {"name": "Ally_1", "type": "player", "hp": 15, "armor_class": 13,
             "dex": 12, "speed": 30, "position": [0, 0], "alignment": alignment},
            {"name": "Ally_2", "type": "player", "hp": 15, "armor_class": 13,
             "dex": 12, "speed": 30, "position": [0, 1], "alignment": alignment},
            {"name": "Enemy_1", "type": "enemy", "hp": 15, "armor_class": 13,
             "dex": 12, "speed": 30, "position": [4, 4], "alignment": "chaotic_evil"},
            {"name": "Enemy_2", "type": "enemy", "hp": 15, "armor_class": 13,
             "dex": 12, "speed": 30, "position": [4, 3], "alignment": "chaotic_evil"},
        ],
        map_size=(5, 5),
        max_rounds=15,
    )


HARNESS_CFG = HarnessConfig(runs=20, seed_start=1, parallel_workers=1)


class TestLawfulGoodBehavior:
    def test_lawful_good_protects_allies(self):
        config = _multi_config("lawful_good")
        result = run_scenario(config, HARNESS_CFG)
        # LG entities should show protective behavior
        for stats in result.get_alignment_stats("lawful good"):
            # Should not betray allies
            assert stats.betrayal_rate < 0.1


class TestChaoticEvilBehavior:
    def test_chaotic_evil_low_mercy(self):
        config = _duel_config("chaotic_evil", "lawful_good")
        result = run_scenario(config, HARNESS_CFG)
        for stats in result.get_alignment_stats("chaotic evil"):
            # CE should have low mercy rate
            assert stats.mercy_rate < 0.5


class TestGoodVsEvilContrast:
    def test_good_shows_more_mercy_than_evil(self):
        good_config = _duel_config("lawful_good", "neutral_evil")
        evil_config = _duel_config("chaotic_evil", "neutral_good")
        good_result = run_scenario(good_config, HARNESS_CFG)
        evil_result = run_scenario(evil_config, HARNESS_CFG)

        good_mercy = 0.0
        evil_mercy = 0.0

        for stats in good_result.get_alignment_stats("lawful good"):
            good_mercy = stats.mercy_rate
        for stats in evil_result.get_alignment_stats("chaotic evil"):
            evil_mercy = stats.mercy_rate

        # Good alignments should show at least as much mercy as evil
        assert good_mercy >= evil_mercy


class TestAlignmentAssertionsAvailable:
    """Verify assertion sets exist for all 9 alignments."""

    @pytest.mark.parametrize("alignment", [
        "lawful good", "neutral good", "chaotic good",
        "lawful neutral", "true neutral", "chaotic neutral",
        "lawful evil", "neutral evil", "chaotic evil",
    ])
    def test_assertions_for_alignment(self, alignment):
        assertions = AlignmentAssertions.for_alignment(alignment)
        assert len(assertions) > 0

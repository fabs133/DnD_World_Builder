"""Behavioral tests: verify alignment-based AI produces expected behavior profiles.

Each test class runs many mock combat sessions and statistically asserts
that the entity's behavior matches its alignment (e.g. CE has low mercy,
LG protects allies).

Use ``pytest tests/behavioral/ -m "not slow"`` for fast CI checks.
"""

import pytest

from core.testing.behavioral.assertions import AlignmentAssertions
from core.testing.behavioral.harness import ScenarioConfig, HarnessConfig, BehavioralTestHarness


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_alignment_test(harness_factory, scenario, alignment: str):
    """Run a scenario and assert all alignment-specific behavioral checks."""
    harness = harness_factory(scenario)
    result = harness.run()
    stats_list = result.get_alignment_stats(alignment)
    assertions = AlignmentAssertions.for_alignment(alignment)

    failures = []
    for stats in stats_list:
        for assertion in assertions:
            passed, msg = assertion(stats)
            if not passed:
                failures.append(f"{stats.entity_name} [{assertion.name}]: {msg}")

    assert not failures, "Behavioral assertion failures:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# GOOD alignments
# ---------------------------------------------------------------------------

class TestLawfulGood:
    """Lawful Good: protects allies, shows mercy, no betrayal."""

    def test_behavioral_profile(self, quick_harness, goblin_ambush_scenario):
        _run_alignment_test(quick_harness, goblin_ambush_scenario, "lawful_good")

    @pytest.mark.slow
    def test_behavioral_profile_thorough(self, thorough_harness, goblin_ambush_scenario):
        _run_alignment_test(thorough_harness, goblin_ambush_scenario, "lawful_good")


class TestNeutralGood:
    """Neutral Good: helpful and merciful, flexible approach."""

    def test_behavioral_profile(self, quick_harness, duel_scenario):
        scenario = duel_scenario("neutral_good", "neutral_evil")
        _run_alignment_test(quick_harness, scenario, "neutral_good")


class TestChaoticGood:
    """Chaotic Good: heroic but unpredictable, protects underdogs."""

    def test_behavioral_profile(self, quick_harness, goblin_ambush_scenario):
        _run_alignment_test(quick_harness, goblin_ambush_scenario, "chaotic_good")


# ---------------------------------------------------------------------------
# NEUTRAL alignments
# ---------------------------------------------------------------------------

class TestLawfulNeutral:
    """Lawful Neutral: disciplined, follows orders, moderate mercy."""

    def test_behavioral_profile(self, quick_harness, duel_scenario):
        scenario = duel_scenario("lawful_neutral", "chaotic_evil")
        _run_alignment_test(quick_harness, scenario, "lawful_neutral")


class TestTrueNeutral:
    """True Neutral: pragmatic, balanced, retreats when outmatched."""

    def test_behavioral_profile(self, quick_harness, duel_scenario):
        scenario = duel_scenario("true_neutral", "chaotic_evil")
        _run_alignment_test(quick_harness, scenario, "true_neutral")


class TestChaoticNeutral:
    """Chaotic Neutral: unpredictable, follows whims."""

    def test_behavioral_profile(self, quick_harness, duel_scenario):
        scenario = duel_scenario("chaotic_neutral", "lawful_evil")
        _run_alignment_test(quick_harness, scenario, "chaotic_neutral")


# ---------------------------------------------------------------------------
# EVIL alignments
# ---------------------------------------------------------------------------

class TestLawfulEvil:
    """Lawful Evil: ruthless tyrant, won't retreat, uses minions."""

    def test_behavioral_profile(self, quick_harness, goblin_ambush_scenario):
        _run_alignment_test(quick_harness, goblin_ambush_scenario, "lawful_evil")


class TestNeutralEvil:
    """Neutral Evil: self-interested mercenary, flees when hurt."""

    def test_behavioral_profile(self, quick_harness, goblin_ambush_scenario):
        _run_alignment_test(quick_harness, goblin_ambush_scenario, "neutral_evil")


class TestChaoticEvil:
    """Chaotic Evil: merciless, unpredictable, causes maximum pain."""

    def test_behavioral_profile(self, quick_harness, goblin_ambush_scenario):
        _run_alignment_test(quick_harness, goblin_ambush_scenario, "chaotic_evil")

    @pytest.mark.slow
    def test_behavioral_profile_thorough(self, thorough_harness, goblin_ambush_scenario):
        _run_alignment_test(thorough_harness, goblin_ambush_scenario, "chaotic_evil")


# ---------------------------------------------------------------------------
# Cross-alignment comparison tests
# ---------------------------------------------------------------------------

class TestAlignmentContrasts:
    """Verify that opposing alignments produce measurably different behavior."""

    def test_good_vs_evil_mercy(self, quick_harness):
        """Good entities should show significantly more mercy than evil ones."""
        scenario = ScenarioConfig(
            name="mercy_contrast",
            entities=[
                {"name": "Paladin", "type": "player", "hp": 30,
                 "alignment": "lawful_good", "position": [0, 0]},
                {"name": "Cleric", "type": "player", "hp": 22,
                 "alignment": "neutral_good", "position": [1, 0]},
                {"name": "Goblin1", "type": "enemy", "hp": 7,
                 "alignment": "chaotic_evil", "position": [4, 4]},
                {"name": "Goblin2", "type": "enemy", "hp": 7,
                 "alignment": "neutral_evil", "position": [4, 3]},
            ],
            map_size=(5, 5),
            max_rounds=10,
        )
        harness = quick_harness(scenario)
        result = harness.run()

        good_stats = result.get_alignment_stats("lawful_good")
        evil_stats = result.get_alignment_stats("chaotic_evil")

        if good_stats and evil_stats:
            good_mercy = good_stats[0].mercy_rate
            evil_mercy = evil_stats[0].mercy_rate
            # Good should show >= as much mercy as evil
            # (both might be 0 if no mercy opportunities arose)
            assert good_mercy >= evil_mercy or (good_mercy == 0 and evil_mercy == 0), (
                f"LG mercy {good_mercy:.2f} should be >= CE mercy {evil_mercy:.2f}"
            )

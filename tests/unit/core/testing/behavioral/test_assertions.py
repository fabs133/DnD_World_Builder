"""Tests for behavioral assertions."""

import pytest

from core.testing.behavioral.assertions import (
    BehaviorAssertion,
    AlignmentAssertions,
)
from core.testing.behavioral.stats import BehaviorEvent, EntityRunStats, BehaviorStats


def _make_stats(entity_name="Test", alignment="true_neutral", events=None):
    """Build a BehaviorStats from a list of (event, count) pairs."""
    run = EntityRunStats(entity_name, alignment, run_id=0, seed=42)
    if events:
        for event, count in events:
            for _ in range(count):
                run.record(1, event)
    return BehaviorStats(entity_name, alignment, runs=[run])


class TestBehaviorAssertion:
    def test_passing_assertion(self):
        assertion = BehaviorAssertion(
            "test_pass",
            lambda s: True,
            lambda s: "should not see this",
        )
        stats = _make_stats()
        passed, msg = assertion(stats)
        assert passed is True
        assert msg == ""

    def test_failing_assertion(self):
        assertion = BehaviorAssertion(
            "test_fail",
            lambda s: False,
            lambda s: "it failed",
        )
        stats = _make_stats()
        passed, msg = assertion(stats)
        assert passed is False
        assert msg == "it failed"


class TestAlignmentAssertionsDispatch:
    @pytest.mark.parametrize("alignment", [
        "lawful_good", "neutral_good", "chaotic_good",
        "lawful_neutral", "true_neutral", "chaotic_neutral",
        "lawful_evil", "neutral_evil", "chaotic_evil",
    ])
    def test_all_alignments_return_assertions(self, alignment):
        assertions = AlignmentAssertions.for_alignment(alignment)
        assert len(assertions) > 0
        assert all(isinstance(a, BehaviorAssertion) for a in assertions)

    def test_unknown_alignment_returns_empty(self):
        assertions = AlignmentAssertions.for_alignment("unknown_alignment")
        assert assertions == []

    def test_accepts_space_separated(self):
        assertions = AlignmentAssertions.for_alignment("lawful good")
        assert len(assertions) > 0


class TestChaoticEvilAssertions:
    def test_pass_with_low_mercy(self):
        stats = _make_stats("CE_Goblin", "chaotic_evil", events=[
            (BehaviorEvent.COULD_EXECUTE_DOWNED, 10),
            (BehaviorEvent.EXECUTED_DOWNED, 9),
            (BehaviorEvent.SPARED_DOWNED, 1),
            (BehaviorEvent.ATTACKED, 5),
            (BehaviorEvent.TARGETED_RANDOM, 3),
            (BehaviorEvent.TARGETED_WEAKEST, 2),
        ])
        for assertion in AlignmentAssertions.chaotic_evil():
            passed, msg = assertion(stats)
            assert passed, f"{assertion.name}: {msg}"

    def test_fail_with_high_mercy(self):
        stats = _make_stats("CE_Goblin", "chaotic_evil", events=[
            (BehaviorEvent.COULD_EXECUTE_DOWNED, 10),
            (BehaviorEvent.SPARED_DOWNED, 9),  # 90% mercy — too high for CE
            (BehaviorEvent.EXECUTED_DOWNED, 1),
        ])
        ce_assertions = AlignmentAssertions.chaotic_evil()
        mercy_assertion = next(a for a in ce_assertions if a.name == "ce_low_mercy")
        passed, msg = mercy_assertion(stats)
        assert not passed


class TestLawfulGoodAssertions:
    def test_pass_with_high_protection(self):
        stats = _make_stats("LG_Paladin", "lawful_good", events=[
            (BehaviorEvent.ALLY_THREATENED, 10),
            (BehaviorEvent.PROTECTED_ALLY, 8),
            (BehaviorEvent.COULD_EXECUTE_DOWNED, 5),
            (BehaviorEvent.SPARED_DOWNED, 4),
        ])
        for assertion in AlignmentAssertions.lawful_good():
            passed, msg = assertion(stats)
            assert passed, f"{assertion.name}: {msg}"

    def test_fail_with_low_protection(self):
        stats = _make_stats("LG_Paladin", "lawful_good", events=[
            (BehaviorEvent.ALLY_THREATENED, 10),
            (BehaviorEvent.PROTECTED_ALLY, 2),  # 20% — too low for LG (threshold > 0.55)
            (BehaviorEvent.IGNORED_DYING_ALLY, 8),
        ])
        lg_assertions = AlignmentAssertions.lawful_good()
        protect_assertion = next(a for a in lg_assertions if a.name == "lg_protects_allies")
        passed, msg = protect_assertion(stats)
        assert not passed


class TestMinSamplesGuard:
    def test_skips_with_few_samples(self):
        """Assertions should pass when there are too few data points."""
        stats = _make_stats("Test", "chaotic_evil", events=[
            (BehaviorEvent.COULD_EXECUTE_DOWNED, 1),
            (BehaviorEvent.SPARED_DOWNED, 1),  # 100% mercy but only 1 sample
        ])
        for assertion in AlignmentAssertions.chaotic_evil():
            passed, msg = assertion(stats)
            assert passed, f"{assertion.name} should skip with few samples: {msg}"

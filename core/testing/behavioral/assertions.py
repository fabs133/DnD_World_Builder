"""Behavioral assertions for alignment-based AI testing.

Thresholds are calibrated to the actual TacticalWeights produced by
Alignment.to_tactical_weights() with +/-15% margin for 10-run variance.
"""

from __future__ import annotations

from typing import Callable

from core.testing.behavioral.stats import BehaviorEvent, BehaviorStats


# Minimum number of relevant opportunities before an assertion applies.
MIN_SAMPLES = 3


class BehaviorAssertion:
    """A named callable that checks a behavioral property of an entity."""

    def __init__(
        self,
        name: str,
        check: Callable[[BehaviorStats], bool],
        message: Callable[[BehaviorStats], str],
    ):
        self.name = name
        self._check = check
        self._message = message

    def __call__(self, stats: BehaviorStats) -> tuple[bool, str]:
        passed = self._check(stats)
        msg = "" if passed else self._message(stats)
        return passed, msg


def _skip_if_few(stats: BehaviorStats, event: BehaviorEvent, threshold: int = MIN_SAMPLES) -> bool:
    """Return True (pass) if there are too few samples to judge."""
    return stats.total(event) < threshold


class AlignmentAssertions:
    """Pre-built behavioral assertions for each D&D alignment.

    Thresholds derived from Alignment.to_tactical_weights():
        LG: flee=0.2, mercy=0.8, protect=0.85
        NG: flee=0.3, mercy=0.8, protect=0.85
        CG: flee=0.15, mercy=0.8, protect=0.85
        LN: flee=0.2, mercy=0.5, protect=0.5
        TN: flee=0.3, mercy=0.5, protect=0.5
        CN: flee=0.4, mercy=0.5, protect=0.5
        LE: flee=0.1, mercy=0.1, protect=0.1
        NE: flee=0.3, mercy=0.1, protect=0.2
        CE: flee=0.4, mercy=0.0, protect=0.2
    """

    # ----- GOOD -----
    # Good alignments: high mercy (0.8), high protection (0.85), low flee

    @staticmethod
    def lawful_good() -> list[BehaviorAssertion]:
        # flee_threshold=0.2, mercy=0.8, ally_protection=0.85
        return [
            BehaviorAssertion(
                "lg_protects_allies",
                lambda s: _skip_if_few(s, BehaviorEvent.ALLY_THREATENED) or s.protect_rate > 0.55,
                lambda s: f"Expected protect_rate > 0.55, got {s.protect_rate:.2f}",
            ),
            BehaviorAssertion(
                "lg_shows_mercy",
                lambda s: _skip_if_few(s, BehaviorEvent.COULD_EXECUTE_DOWNED) or s.mercy_rate > 0.55,
                lambda s: f"Expected mercy_rate > 0.55, got {s.mercy_rate:.2f}",
            ),
            BehaviorAssertion(
                "lg_no_betrayal",
                lambda s: _skip_if_few(s, BehaviorEvent.ALLY_THREATENED) or s.betrayal_rate < 0.1,
                lambda s: f"Expected betrayal_rate < 0.1, got {s.betrayal_rate:.2f}",
            ),
            BehaviorAssertion(
                "lg_low_flee",
                lambda s: _skip_if_few(s, BehaviorEvent.CONSIDERED_FLEEING) or s.flee_rate < 0.35,
                lambda s: f"Expected flee_rate < 0.35, got {s.flee_rate:.2f}",
            ),
        ]

    @staticmethod
    def neutral_good() -> list[BehaviorAssertion]:
        # flee_threshold=0.3, mercy=0.8, ally_protection=0.85
        return [
            BehaviorAssertion(
                "ng_protects_allies",
                lambda s: _skip_if_few(s, BehaviorEvent.ALLY_THREATENED) or s.protect_rate > 0.5,
                lambda s: f"Expected protect_rate > 0.5, got {s.protect_rate:.2f}",
            ),
            BehaviorAssertion(
                "ng_shows_mercy",
                lambda s: _skip_if_few(s, BehaviorEvent.COULD_EXECUTE_DOWNED) or s.mercy_rate > 0.55,
                lambda s: f"Expected mercy_rate > 0.55, got {s.mercy_rate:.2f}",
            ),
            BehaviorAssertion(
                "ng_no_betrayal",
                lambda s: _skip_if_few(s, BehaviorEvent.ALLY_THREATENED) or s.betrayal_rate < 0.1,
                lambda s: f"Expected betrayal_rate < 0.1, got {s.betrayal_rate:.2f}",
            ),
            BehaviorAssertion(
                "ng_moderate_flee",
                lambda s: _skip_if_few(s, BehaviorEvent.CONSIDERED_FLEEING) or s.flee_rate <= 0.45,
                lambda s: f"Expected flee_rate <= 0.45, got {s.flee_rate:.2f}",
            ),
        ]

    @staticmethod
    def chaotic_good() -> list[BehaviorAssertion]:
        # flee_threshold=0.15, mercy=0.8, ally_protection=0.85
        return [
            BehaviorAssertion(
                "cg_protects_allies",
                lambda s: _skip_if_few(s, BehaviorEvent.ALLY_THREATENED) or s.protect_rate > 0.5,
                lambda s: f"Expected protect_rate > 0.5, got {s.protect_rate:.2f}",
            ),
            BehaviorAssertion(
                "cg_shows_mercy",
                lambda s: _skip_if_few(s, BehaviorEvent.COULD_EXECUTE_DOWNED) or s.mercy_rate > 0.55,
                lambda s: f"Expected mercy_rate > 0.55, got {s.mercy_rate:.2f}",
            ),
            BehaviorAssertion(
                "cg_no_betrayal",
                lambda s: _skip_if_few(s, BehaviorEvent.ALLY_THREATENED) or s.betrayal_rate < 0.1,
                lambda s: f"Expected betrayal_rate < 0.1, got {s.betrayal_rate:.2f}",
            ),
            BehaviorAssertion(
                "cg_low_flee",
                lambda s: _skip_if_few(s, BehaviorEvent.CONSIDERED_FLEEING) or s.flee_rate < 0.3,
                lambda s: f"Expected flee_rate < 0.3, got {s.flee_rate:.2f}",
            ),
        ]

    # ----- NEUTRAL -----
    # Neutral alignments: moderate mercy (0.5), moderate protection (0.5)

    @staticmethod
    def lawful_neutral() -> list[BehaviorAssertion]:
        # flee_threshold=0.2, mercy=0.5, ally_protection=0.5
        return [
            BehaviorAssertion(
                "ln_moderate_mercy",
                lambda s: _skip_if_few(s, BehaviorEvent.COULD_EXECUTE_DOWNED) or 0.25 <= s.mercy_rate <= 0.75,
                lambda s: f"Expected mercy_rate in [0.25, 0.75], got {s.mercy_rate:.2f}",
            ),
            BehaviorAssertion(
                "ln_moderate_protect",
                lambda s: _skip_if_few(s, BehaviorEvent.ALLY_THREATENED) or 0.2 <= s.protect_rate <= 0.75,
                lambda s: f"Expected protect_rate in [0.2, 0.75], got {s.protect_rate:.2f}",
            ),
            BehaviorAssertion(
                "ln_low_betrayal",
                lambda s: _skip_if_few(s, BehaviorEvent.ALLY_THREATENED) or s.betrayal_rate < 0.15,
                lambda s: f"Expected betrayal_rate < 0.15, got {s.betrayal_rate:.2f}",
            ),
            BehaviorAssertion(
                "ln_low_flee",
                lambda s: _skip_if_few(s, BehaviorEvent.CONSIDERED_FLEEING) or s.flee_rate < 0.35,
                lambda s: f"Expected flee_rate < 0.35, got {s.flee_rate:.2f}",
            ),
        ]

    @staticmethod
    def true_neutral() -> list[BehaviorAssertion]:
        # flee_threshold=0.3, mercy=0.5, ally_protection=0.5
        return [
            BehaviorAssertion(
                "tn_moderate_mercy",
                lambda s: _skip_if_few(s, BehaviorEvent.COULD_EXECUTE_DOWNED) or 0.25 <= s.mercy_rate <= 0.75,
                lambda s: f"Expected mercy_rate in [0.25, 0.75], got {s.mercy_rate:.2f}",
            ),
            BehaviorAssertion(
                "tn_moderate_protect",
                lambda s: _skip_if_few(s, BehaviorEvent.ALLY_THREATENED) or 0.2 <= s.protect_rate <= 0.75,
                lambda s: f"Expected protect_rate in [0.2, 0.75], got {s.protect_rate:.2f}",
            ),
            BehaviorAssertion(
                "tn_low_betrayal",
                lambda s: _skip_if_few(s, BehaviorEvent.ALLY_THREATENED) or s.betrayal_rate < 0.2,
                lambda s: f"Expected betrayal_rate < 0.2, got {s.betrayal_rate:.2f}",
            ),
            BehaviorAssertion(
                "tn_moderate_flee",
                lambda s: _skip_if_few(s, BehaviorEvent.CONSIDERED_FLEEING) or s.flee_rate < 0.5,
                lambda s: f"Expected flee_rate < 0.5, got {s.flee_rate:.2f}",
            ),
        ]

    @staticmethod
    def chaotic_neutral() -> list[BehaviorAssertion]:
        # flee_threshold=0.4, mercy=0.5, ally_protection=0.5, predictability=0.2
        return [
            BehaviorAssertion(
                "cn_moderate_mercy",
                lambda s: _skip_if_few(s, BehaviorEvent.COULD_EXECUTE_DOWNED) or 0.25 <= s.mercy_rate <= 0.75,
                lambda s: f"Expected mercy_rate in [0.25, 0.75], got {s.mercy_rate:.2f}",
            ),
            BehaviorAssertion(
                "cn_moderate_protect",
                lambda s: _skip_if_few(s, BehaviorEvent.ALLY_THREATENED) or 0.2 <= s.protect_rate <= 0.75,
                lambda s: f"Expected protect_rate in [0.2, 0.75], got {s.protect_rate:.2f}",
            ),
            BehaviorAssertion(
                "cn_low_betrayal",
                lambda s: _skip_if_few(s, BehaviorEvent.ALLY_THREATENED) or s.betrayal_rate < 0.3,
                lambda s: f"Expected betrayal_rate < 0.3, got {s.betrayal_rate:.2f}",
            ),
            BehaviorAssertion(
                "cn_moderate_flee",
                lambda s: _skip_if_few(s, BehaviorEvent.CONSIDERED_FLEEING) or s.flee_rate < 0.6,
                lambda s: f"Expected flee_rate < 0.6, got {s.flee_rate:.2f}",
            ),
        ]

    # ----- EVIL -----
    # Evil alignments: low mercy (0.0-0.1), low protection (0.1-0.2)

    @staticmethod
    def lawful_evil() -> list[BehaviorAssertion]:
        # flee_threshold=0.1, mercy=0.1, ally_protection=0.1
        return [
            BehaviorAssertion(
                "le_low_mercy",
                lambda s: _skip_if_few(s, BehaviorEvent.COULD_EXECUTE_DOWNED) or s.mercy_rate < 0.3,
                lambda s: f"Expected mercy_rate < 0.3, got {s.mercy_rate:.2f}",
            ),
            BehaviorAssertion(
                "le_low_protect",
                lambda s: _skip_if_few(s, BehaviorEvent.ALLY_THREATENED) or s.protect_rate < 0.3,
                lambda s: f"Expected protect_rate < 0.3, got {s.protect_rate:.2f}",
            ),
            BehaviorAssertion(
                "le_low_betrayal",
                lambda s: _skip_if_few(s, BehaviorEvent.ALLY_THREATENED) or s.betrayal_rate < 0.2,
                lambda s: f"Expected betrayal_rate < 0.2, got {s.betrayal_rate:.2f}",
            ),
            BehaviorAssertion(
                "le_rarely_flees",
                lambda s: _skip_if_few(s, BehaviorEvent.CONSIDERED_FLEEING) or s.flee_rate < 0.25,
                lambda s: f"Expected flee_rate < 0.25, got {s.flee_rate:.2f}",
            ),
        ]

    @staticmethod
    def neutral_evil() -> list[BehaviorAssertion]:
        # flee_threshold=0.3, mercy=0.1, ally_protection=0.2
        return [
            BehaviorAssertion(
                "ne_low_mercy",
                lambda s: _skip_if_few(s, BehaviorEvent.COULD_EXECUTE_DOWNED) or s.mercy_rate < 0.25,
                lambda s: f"Expected mercy_rate < 0.25, got {s.mercy_rate:.2f}",
            ),
            BehaviorAssertion(
                "ne_low_protect",
                lambda s: _skip_if_few(s, BehaviorEvent.ALLY_THREATENED) or s.protect_rate < 0.4,
                lambda s: f"Expected protect_rate < 0.4, got {s.protect_rate:.2f}",
            ),
            BehaviorAssertion(
                "ne_moderate_flee",
                lambda s: _skip_if_few(s, BehaviorEvent.CONSIDERED_FLEEING) or s.flee_rate >= 0.10,
                lambda s: f"Expected flee_rate >= 0.10, got {s.flee_rate:.2f}",
            ),
        ]

    @staticmethod
    def chaotic_evil() -> list[BehaviorAssertion]:
        # flee_threshold=0.4, mercy=0.0, ally_protection=0.2, predictability=0.1
        return [
            BehaviorAssertion(
                "ce_low_mercy",
                lambda s: _skip_if_few(s, BehaviorEvent.COULD_EXECUTE_DOWNED) or s.mercy_rate < 0.15,
                lambda s: f"Expected mercy_rate < 0.15, got {s.mercy_rate:.2f}",
            ),
            BehaviorAssertion(
                "ce_low_protect",
                lambda s: _skip_if_few(s, BehaviorEvent.ALLY_THREATENED) or s.protect_rate < 0.4,
                lambda s: f"Expected protect_rate < 0.4, got {s.protect_rate:.2f}",
            ),
            BehaviorAssertion(
                "ce_unpredictable",
                lambda s: s.total(BehaviorEvent.ATTACKED) < MIN_SAMPLES or s.target_entropy > 0.1,
                lambda s: f"Expected target_entropy > 0.1, got {s.target_entropy:.2f}",
            ),
            BehaviorAssertion(
                "ce_moderate_flee",
                lambda s: _skip_if_few(s, BehaviorEvent.CONSIDERED_FLEEING) or s.flee_rate < 0.6,
                lambda s: f"Expected flee_rate < 0.6, got {s.flee_rate:.2f}",
            ),
        ]

    # ----- DISPATCHER -----

    @staticmethod
    def for_alignment(alignment: str) -> list[BehaviorAssertion]:
        """Get assertions for any alignment string."""
        normalized = alignment.lower().replace(" ", "_")
        dispatch = {
            "lawful_good": AlignmentAssertions.lawful_good,
            "neutral_good": AlignmentAssertions.neutral_good,
            "chaotic_good": AlignmentAssertions.chaotic_good,
            "lawful_neutral": AlignmentAssertions.lawful_neutral,
            "true_neutral": AlignmentAssertions.true_neutral,
            "chaotic_neutral": AlignmentAssertions.chaotic_neutral,
            "lawful_evil": AlignmentAssertions.lawful_evil,
            "neutral_evil": AlignmentAssertions.neutral_evil,
            "chaotic_evil": AlignmentAssertions.chaotic_evil,
        }
        factory = dispatch.get(normalized)
        if factory is None:
            return []
        return factory()

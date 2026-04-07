"""Tests for choreography sequence data model — no Qt needed."""

from ui.animations.choreography_data import (
    ChoreographyPhase, ChoreographyEffect, EffectType,
    PhaseStep, ChoreographySequence,
    MELEE_HIT, MELEE_CRIT, MELEE_MISS, SPELL_HIT, HEAL,
    SIMPLE_ACTION, SEQUENCE_REGISTRY,
)


class TestPhaseStep:
    def test_default_duration(self):
        step = PhaseStep(phase=ChoreographyPhase.INTENT)
        assert step.duration_ms == 300

    def test_frozen(self):
        step = PhaseStep(phase=ChoreographyPhase.IMPACT)
        try:
            step.duration_ms = 999
            assert False, "Should be frozen"
        except AttributeError:
            pass


class TestChoreographySequence:
    def test_total_duration(self):
        seq = ChoreographySequence(
            name="test",
            steps=(
                PhaseStep(ChoreographyPhase.INTENT, 100),
                PhaseStep(ChoreographyPhase.IMPACT, 200),
            ),
        )
        assert seq.total_duration_ms == 300

    def test_melee_hit_has_four_phases(self):
        assert len(MELEE_HIT.steps) == 4

    def test_melee_hit_total_is_850ms(self):
        assert MELEE_HIT.total_duration_ms == 850

    def test_miss_shorter_than_hit(self):
        assert MELEE_MISS.total_duration_ms < MELEE_HIT.total_duration_ms

    def test_crit_same_as_hit(self):
        assert MELEE_CRIT.total_duration_ms == MELEE_HIT.total_duration_ms

    def test_simple_action_short(self):
        assert SIMPLE_ACTION.total_duration_ms <= 300

    def test_all_sequences_have_phases(self):
        for seq in (MELEE_HIT, MELEE_CRIT, MELEE_MISS,
                    SPELL_HIT, HEAL, SIMPLE_ACTION):
            assert len(seq.steps) >= 1

    def test_registry_contains_all(self):
        assert "melee_hit" in SEQUENCE_REGISTRY
        assert "melee_miss" in SEQUENCE_REGISTRY
        assert "simple" in SEQUENCE_REGISTRY
        assert len(SEQUENCE_REGISTRY) == 6

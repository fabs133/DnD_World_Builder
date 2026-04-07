"""Tests for transition specs and registry."""

import re

from ui.transitions.transition_spec import TransitionSpec, TransitionType
from ui.transitions.transition_registry import (
    TRANSITIONS, get_transition, list_transitions,
)


class TestTransitionRegistry:

    def test_all_21_transitions_registered(self):
        assert len(TRANSITIONS) == 22

    def test_get_transition_returns_spec(self):
        spec = get_transition("exploration_to_combat")
        assert isinstance(spec, TransitionSpec)
        assert spec.name == "Enter combat mode"

    def test_get_transition_unknown_returns_none(self):
        assert get_transition("nonexistent") is None

    def test_list_transitions_returns_all_ids(self):
        ids = list_transitions()
        assert "exploration_to_combat" in ids
        assert "turn_advance" in ids
        assert len(ids) == 22


class TestCinematicTransitions:

    def test_cinematic_transitions_have_theme_swap(self):
        cinematics = [
            s for s in TRANSITIONS.values()
            if s.transition_type == TransitionType.CINEMATIC
        ]
        assert len(cinematics) == 3
        for spec in cinematics:
            assert spec.theme_before is not None
            assert spec.theme_after is not None

    def test_cinematic_transitions_have_sound(self):
        cinematics = [
            s for s in TRANSITIONS.values()
            if s.transition_type == TransitionType.CINEMATIC
        ]
        for spec in cinematics:
            assert spec.sound_id is not None

    def test_combat_enter_has_dust_and_shake(self):
        spec = get_transition("exploration_to_combat")
        assert spec.dust_particles is True
        assert spec.shake_frames == 5


class TestCutTransitions:

    def test_cut_transitions_have_zero_duration(self):
        cuts = [
            s for s in TRANSITIONS.values()
            if s.transition_type == TransitionType.CUT
        ]
        for spec in cuts:
            assert spec.duration_ms == 0, f"{spec.name} is CUT but has duration {spec.duration_ms}"


class TestSoundIds:

    def test_all_sound_ids_are_valid_filenames(self):
        """Sound IDs should be simple lowercase identifiers."""
        pattern = re.compile(r"^[a-z][a-z0-9_]*$")
        for tid, spec in TRANSITIONS.items():
            if spec.sound_id is not None:
                assert pattern.match(spec.sound_id), (
                    f"Transition '{tid}' has invalid sound_id: '{spec.sound_id}'"
                )

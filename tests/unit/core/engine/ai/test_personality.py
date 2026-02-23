"""Tests for unified personality system via engine package."""

import pytest
from core.engine.ai import (
    EntityPersonality,
    Personality,
    Alignment,
    TacticalWeights,
    LAWFUL_GOOD,
    CHAOTIC_EVIL,
    TRUE_NEUTRAL,
    # Legacy presets
    AGGRESSIVE,
    DEFENSIVE,
    TACTICAL,
    BERSERKER,
)


class TestPersonalityReexports:
    """Verify that personality re-exports work correctly."""

    def test_entity_personality_available(self):
        p = EntityPersonality(Alignment.LAWFUL_GOOD)
        assert p.archetype == "Protector"

    def test_personality_alias(self):
        # Personality should be an alias for EntityPersonality
        assert Personality is EntityPersonality

    def test_alignment_presets(self):
        assert LAWFUL_GOOD.alignment == Alignment.LAWFUL_GOOD
        assert CHAOTIC_EVIL.alignment == Alignment.CHAOTIC_EVIL
        assert TRUE_NEUTRAL.alignment == Alignment.TRUE_NEUTRAL

    def test_legacy_presets_exist(self):
        # Legacy presets should map to reasonable alignments
        assert AGGRESSIVE is not None
        assert DEFENSIVE is not None
        assert TACTICAL is not None
        assert BERSERKER is not None

    def test_tactical_weights_from_alignment(self):
        p = EntityPersonality(Alignment.CHAOTIC_EVIL)
        weights = p.tactical_weights
        assert isinstance(weights, TacticalWeights)
        # Chaotic Evil: low mercy, high aggression
        assert weights.mercy < 0.3
        assert weights.aggression > 0.7


class TestAlignmentGrid:
    """Test the 9-alignment grid."""

    def test_all_alignments_have_archetypes(self):
        alignments = [
            Alignment.LAWFUL_GOOD,
            Alignment.NEUTRAL_GOOD,
            Alignment.CHAOTIC_GOOD,
            Alignment.LAWFUL_NEUTRAL,
            Alignment.TRUE_NEUTRAL,
            Alignment.CHAOTIC_NEUTRAL,
            Alignment.LAWFUL_EVIL,
            Alignment.NEUTRAL_EVIL,
            Alignment.CHAOTIC_EVIL,
        ]
        for alignment in alignments:
            p = EntityPersonality(alignment)
            assert p.archetype, f"No archetype for {alignment}"

    def test_alignment_short_codes(self):
        assert Alignment.LAWFUL_GOOD.short_code == "LG"
        assert Alignment.CHAOTIC_EVIL.short_code == "CE"
        assert Alignment.TRUE_NEUTRAL.short_code == "TN"

    def test_alignment_from_string(self):
        assert Alignment.from_string("lawful good") == Alignment.LAWFUL_GOOD
        assert Alignment.from_string("CE") == Alignment.CHAOTIC_EVIL
        assert Alignment.from_string("true neutral") == Alignment.TRUE_NEUTRAL


class TestPersonalityForPrompt:
    """Test prompt formatting."""

    def test_format_includes_alignment(self):
        p = EntityPersonality(Alignment.NEUTRAL_EVIL)
        text = p.format_for_prompt()
        assert "Neutral Evil" in text
        assert "Mercenary" in text

    def test_format_includes_will_do(self):
        p = EntityPersonality(Alignment.LAWFUL_GOOD)
        text = p.format_for_prompt()
        assert "WILL DO:" in text
        assert "WON'T DO:" in text

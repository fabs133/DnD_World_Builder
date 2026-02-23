# tests/unit/models/ai/test_alignment.py
"""Tests for the D&D alignment system."""

import pytest
from models.ai.alignment import Alignment, LawChaos, GoodEvil


class TestAlignmentBasics:
    """Test basic alignment creation and properties."""
    
    def test_create_alignment_from_enums(self):
        alignment = Alignment(LawChaos.CHAOTIC, GoodEvil.EVIL)
        assert alignment.law_chaos == LawChaos.CHAOTIC
        assert alignment.good_evil == GoodEvil.EVIL
    
    def test_alignment_name_standard(self):
        alignment = Alignment(LawChaos.LAWFUL, GoodEvil.GOOD)
        assert alignment.name == "Lawful Good"
    
    def test_alignment_name_true_neutral(self):
        alignment = Alignment(LawChaos.NEUTRAL, GoodEvil.NEUTRAL)
        assert alignment.name == "True Neutral"
    
    def test_short_codes(self):
        assert Alignment(LawChaos.LAWFUL, GoodEvil.GOOD).short_code == "LG"
        assert Alignment(LawChaos.CHAOTIC, GoodEvil.EVIL).short_code == "CE"
        assert Alignment(LawChaos.NEUTRAL, GoodEvil.NEUTRAL).short_code == "TN"
        assert Alignment(LawChaos.NEUTRAL, GoodEvil.EVIL).short_code == "NE"


class TestAlignmentNamedConstructors:
    """Test the named constructor class properties."""
    
    def test_lawful_good(self):
        lg = Alignment.LAWFUL_GOOD
        assert lg.law_chaos == LawChaos.LAWFUL
        assert lg.good_evil == GoodEvil.GOOD
        assert lg.name == "Lawful Good"
    
    def test_chaotic_evil(self):
        ce = Alignment.CHAOTIC_EVIL
        assert ce.law_chaos == LawChaos.CHAOTIC
        assert ce.good_evil == GoodEvil.EVIL
        assert ce.name == "Chaotic Evil"
    
    def test_true_neutral(self):
        tn = Alignment.TRUE_NEUTRAL
        assert tn.law_chaos == LawChaos.NEUTRAL
        assert tn.good_evil == GoodEvil.NEUTRAL
        assert tn.name == "True Neutral"
    
    def test_all_nine_alignments_exist(self):
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
        assert len(alignments) == 9
        # All should be distinct
        names = [a.name for a in alignments]
        assert len(set(names)) == 9


class TestAlignmentParsing:
    """Test parsing alignments from strings."""
    
    def test_parse_full_name(self):
        assert Alignment.from_string("lawful good") == Alignment.LAWFUL_GOOD
        assert Alignment.from_string("chaotic evil") == Alignment.CHAOTIC_EVIL
    
    def test_parse_mixed_case(self):
        assert Alignment.from_string("Lawful Good") == Alignment.LAWFUL_GOOD
        assert Alignment.from_string("CHAOTIC EVIL") == Alignment.CHAOTIC_EVIL
    
    def test_parse_short_codes(self):
        assert Alignment.from_string("LG") == Alignment.LAWFUL_GOOD
        assert Alignment.from_string("CE") == Alignment.CHAOTIC_EVIL
        assert Alignment.from_string("TN") == Alignment.TRUE_NEUTRAL
        assert Alignment.from_string("lg") == Alignment.LAWFUL_GOOD
    
    def test_parse_true_neutral_variants(self):
        assert Alignment.from_string("true neutral") == Alignment.TRUE_NEUTRAL
        assert Alignment.from_string("neutral") == Alignment.TRUE_NEUTRAL
        assert Alignment.from_string("N") == Alignment.TRUE_NEUTRAL
    
    def test_parse_invalid_raises(self):
        with pytest.raises(ValueError):
            Alignment.from_string("super evil")
        with pytest.raises(ValueError):
            Alignment.from_string("xyz")


class TestAlignmentSerialization:
    """Test serialization and deserialization."""
    
    def test_to_dict(self):
        alignment = Alignment.CHAOTIC_GOOD
        data = alignment.to_dict()
        assert data == {"law_chaos": "chaotic", "good_evil": "good"}
    
    def test_from_dict(self):
        data = {"law_chaos": "lawful", "good_evil": "evil"}
        alignment = Alignment.from_dict(data)
        assert alignment == Alignment.LAWFUL_EVIL
    
    def test_roundtrip(self):
        original = Alignment.NEUTRAL_GOOD
        data = original.to_dict()
        restored = Alignment.from_dict(data)
        assert restored == original


class TestAlignmentTacticalWeights:
    """Test tactical weight generation from alignment."""
    
    def test_lawful_good_weights(self):
        weights = Alignment.LAWFUL_GOOD.to_tactical_weights()
        # Lawful Good: high coordination, ally protection, honor
        assert weights.coordination >= 0.7
        assert weights.ally_protection >= 0.7
        assert weights.honor >= 0.6
        assert weights.mercy >= 0.6
    
    def test_chaotic_evil_weights(self):
        weights = Alignment.CHAOTIC_EVIL.to_tactical_weights()
        # Chaotic Evil: low coordination, no mercy, unpredictable
        assert weights.coordination <= 0.3
        assert weights.mercy <= 0.2
        assert weights.predictability <= 0.3
        assert weights.aggression >= 0.7
    
    def test_true_neutral_weights(self):
        weights = Alignment.TRUE_NEUTRAL.to_tactical_weights()
        # True Neutral: balanced everything
        assert 0.4 <= weights.coordination <= 0.6
        assert 0.4 <= weights.aggression <= 0.6
    
    def test_lawful_evil_tyrant_special_case(self):
        weights = Alignment.LAWFUL_EVIL.to_tactical_weights()
        # Tyrant: uses minions as pawns, won't retreat
        assert weights.ally_protection <= 0.2  # Uses minions as shields
        assert weights.flee_threshold <= 0.15  # Won't flee (shows weakness)
    
    def test_weights_are_valid(self):
        """All weights should be in [0, 1] range."""
        for lc in LawChaos:
            for ge in GoodEvil:
                alignment = Alignment(lc, ge)
                weights = alignment.to_tactical_weights()
                for field_name in weights.to_dict():
                    value = getattr(weights, field_name)
                    assert 0.0 <= value <= 1.0, f"{alignment.name}.{field_name} = {value}"

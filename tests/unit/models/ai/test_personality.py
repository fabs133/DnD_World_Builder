# tests/unit/models/ai/test_personality.py
"""Tests for the entity personality system."""

import pytest
from models.ai.alignment import Alignment
from models.ai.personality import EntityPersonality, ALIGNMENT_BEHAVIORS
from models.ai.tactical_weights import TacticalWeights


class TestPersonalityBasics:
    """Test basic personality creation."""
    
    def test_create_personality(self):
        p = EntityPersonality(alignment=Alignment.LAWFUL_GOOD)
        assert p.alignment == Alignment.LAWFUL_GOOD
        assert p.archetype == "Protector"
    
    def test_create_with_traits(self):
        p = EntityPersonality(
            alignment=Alignment.CHAOTIC_EVIL,
            trait="Cackles maniacally",
            bond="Chaos itself",
            flaw="Easily distracted by destruction",
        )
        assert p.trait == "Cackles maniacally"
        assert p.bond == "Chaos itself"
        assert p.flaw == "Easily distracted by destruction"
    
    def test_archetype_from_alignment(self):
        assert EntityPersonality(Alignment.LAWFUL_GOOD).archetype == "Protector"
        assert EntityPersonality(Alignment.NEUTRAL_EVIL).archetype == "Mercenary"
        assert EntityPersonality(Alignment.CHAOTIC_EVIL).archetype == "Agent of Chaos"


class TestAlignmentBehaviors:
    """Test the ALIGNMENT_BEHAVIORS data structure."""
    
    def test_all_nine_alignments_have_behaviors(self):
        expected_keys = [
            ("lawful", "good"),
            ("neutral", "good"),
            ("chaotic", "good"),
            ("lawful", "neutral"),
            ("neutral", "neutral"),
            ("chaotic", "neutral"),
            ("lawful", "evil"),
            ("neutral", "evil"),
            ("chaotic", "evil"),
        ]
        for key in expected_keys:
            assert key in ALIGNMENT_BEHAVIORS, f"Missing behaviors for {key}"
    
    def test_behaviors_have_required_fields(self):
        required_fields = ["archetype", "tagline", "tactics", "will_do", "wont_do"]
        for key, behaviors in ALIGNMENT_BEHAVIORS.items():
            for field in required_fields:
                assert field in behaviors, f"Missing {field} for {key}"
    
    def test_will_do_and_wont_do_are_lists(self):
        for key, behaviors in ALIGNMENT_BEHAVIORS.items():
            assert isinstance(behaviors["will_do"], list)
            assert isinstance(behaviors["wont_do"], list)
            assert len(behaviors["will_do"]) >= 3  # At least 3 items
            assert len(behaviors["wont_do"]) >= 3


class TestPersonalityBehaviors:
    """Test personality behavior properties."""
    
    def test_will_do_from_alignment(self):
        p = EntityPersonality(Alignment.LAWFUL_GOOD)
        assert "Shield fallen allies" in p.will_do
    
    def test_wont_do_from_alignment(self):
        p = EntityPersonality(Alignment.CHAOTIC_EVIL)
        assert "Show mercy" in p.wont_do
    
    def test_voice_lines(self):
        p = EntityPersonality(Alignment.CHAOTIC_EVIL)
        assert len(p.voice_lines) > 0
        # Chaotic Evil should have some... colorful... lines
        assert any("burn" in line.lower() or "hehe" in line.lower() for line in p.voice_lines)
    
    def test_tactics_description(self):
        p = EntityPersonality(Alignment.NEUTRAL_EVIL)
        assert "calculating" in p.tactics_description.lower()


class TestPersonalityRelationships:
    """Test the relationship system."""
    
    def test_add_relationship(self):
        p = EntityPersonality(Alignment.LAWFUL_GOOD)
        p.add_relationship("Fighter", "sworn to protect")
        assert p.get_relationship("Fighter") == "sworn to protect"
    
    def test_get_nonexistent_relationship(self):
        p = EntityPersonality(Alignment.LAWFUL_GOOD)
        assert p.get_relationship("Nobody") is None
    
    def test_update_relationship(self):
        p = EntityPersonality(Alignment.NEUTRAL_EVIL)
        p.add_relationship("Target", "hired to kill")
        p.add_relationship("Target", "contract cancelled")
        assert p.get_relationship("Target") == "contract cancelled"


class TestPersonalityTacticalWeights:
    """Test tactical weight integration."""
    
    def test_weights_from_alignment(self):
        p = EntityPersonality(Alignment.CHAOTIC_GOOD)
        weights = p.tactical_weights
        assert isinstance(weights, TacticalWeights)
        # Chaotic Good: low coordination, high self-sacrifice
        assert weights.coordination < 0.4
        assert weights.self_sacrifice > 0.6
    
    def test_custom_weights_override(self):
        p = EntityPersonality(Alignment.TRUE_NEUTRAL)
        
        # Default weights
        default_weights = p.tactical_weights
        
        # Set custom weights
        custom = TacticalWeights(aggression=0.9, mercy=0.0, flee_threshold=0.0)
        p.set_custom_weights(custom)
        
        assert p.tactical_weights.aggression == 0.9
        assert p.tactical_weights.mercy == 0.0
    
    def test_clear_custom_weights(self):
        p = EntityPersonality(Alignment.LAWFUL_GOOD)
        original_mercy = p.tactical_weights.mercy
        
        # Override
        p.set_custom_weights(TacticalWeights(mercy=0.0))
        assert p.tactical_weights.mercy == 0.0
        
        # Clear
        p.clear_custom_weights()
        assert p.tactical_weights.mercy == original_mercy


class TestPersonalitySerialization:
    """Test serialization and deserialization."""
    
    def test_to_dict_minimal(self):
        p = EntityPersonality(Alignment.TRUE_NEUTRAL)
        data = p.to_dict()
        
        assert "alignment" in data
        assert data["alignment"]["law_chaos"] == "neutral"
        assert data["alignment"]["good_evil"] == "neutral"
    
    def test_to_dict_full(self):
        p = EntityPersonality(
            alignment=Alignment.LAWFUL_EVIL,
            trait="Imperious",
            bond="The throne",
            flaw="Underestimates peasants",
            ideal="Power",
        )
        p.add_relationship("Minion", "expendable")
        
        data = p.to_dict()
        
        assert data["trait"] == "Imperious"
        assert data["bond"] == "The throne"
        assert data["flaw"] == "Underestimates peasants"
        assert data["ideal"] == "Power"
        assert data["relationships"]["Minion"] == "expendable"
    
    def test_from_dict(self):
        data = {
            "alignment": {"law_chaos": "chaotic", "good_evil": "good"},
            "trait": "Rebellious",
            "bond": "Freedom",
            "flaw": "Reckless",
            "ideal": "Liberty",
            "relationships": {"Tyrant": "enemy"},
        }
        
        p = EntityPersonality.from_dict(data)
        
        assert p.alignment == Alignment.CHAOTIC_GOOD
        assert p.trait == "Rebellious"
        assert p.get_relationship("Tyrant") == "enemy"
    
    def test_roundtrip(self):
        original = EntityPersonality(
            alignment=Alignment.NEUTRAL_GOOD,
            trait="Helpful",
            bond="The sick and wounded",
            flaw="Cannot refuse a plea for help",
        )
        original.add_relationship("Patient", "must heal")
        
        data = original.to_dict()
        restored = EntityPersonality.from_dict(data)
        
        assert restored.alignment == original.alignment
        assert restored.trait == original.trait
        assert restored.get_relationship("Patient") == "must heal"
    
    def test_roundtrip_with_custom_weights(self):
        original = EntityPersonality(Alignment.TRUE_NEUTRAL)
        original.set_custom_weights(TacticalWeights(aggression=0.1, mercy=0.9))
        
        data = original.to_dict()
        restored = EntityPersonality.from_dict(data)
        
        assert restored.tactical_weights.aggression == 0.1
        assert restored.tactical_weights.mercy == 0.9


class TestPersonalityPresets:
    """Test the preset personality archetypes."""
    
    def test_goblin_grunt(self):
        p = EntityPersonality.goblin_grunt()
        assert p.alignment == Alignment.NEUTRAL_EVIL
        assert "panic" in p.flaw.lower() or "coward" in p.trait.lower() or "nervous" in p.trait.lower()
    
    def test_goblin_shaman(self):
        p = EntityPersonality.goblin_shaman()
        assert p.alignment == Alignment.LAWFUL_EVIL
        assert len(p.relationships) > 0  # Should have relationship with guards
    
    def test_paladin_companion(self):
        p = EntityPersonality.paladin_companion()
        assert p.alignment == Alignment.LAWFUL_GOOD
        assert "protect" in p.bond.lower()
    
    def test_undead_minion_has_custom_weights(self):
        p = EntityPersonality.undead_minion()
        weights = p.tactical_weights
        # Mindless: never flees, no self-preservation
        assert weights.flee_threshold == 0.0
        assert weights.self_sacrifice == 1.0


class TestPersonalityPromptFormat:
    """Test the prompt formatting."""
    
    def test_format_for_prompt(self):
        p = EntityPersonality(
            alignment=Alignment.LAWFUL_GOOD,
            trait="Stoic and brave",
            bond="My comrades",
            flaw="Too trusting",
        )
        
        prompt_text = p.format_for_prompt()
        
        assert "Lawful Good" in prompt_text
        assert "Protector" in prompt_text
        assert "Stoic and brave" in prompt_text
        assert "WILL DO:" in prompt_text
        assert "WON'T DO:" in prompt_text
    
    def test_format_includes_relationships(self):
        p = EntityPersonality(Alignment.LAWFUL_EVIL)
        p.add_relationship("Minion A", "expendable pawn")
        p.add_relationship("Minion B", "useful idiot")
        
        prompt_text = p.format_for_prompt()
        
        assert "RELATIONSHIPS:" in prompt_text
        assert "Minion A" in prompt_text
        assert "expendable pawn" in prompt_text

"""Tests for GameEntity voice_profile and dialogue_lines integration."""

from models.entities.game_entity import GameEntity
from core.voice.voice_profile import VoiceProfile


class TestGameEntityVoice:

    def test_entity_without_voice_backward_compat(self):
        """Old entity JSON without voice_profile loads fine."""
        data = {
            "name": "OldNPC",
            "entity_type": "npc",
            "stats": {"hp": 10},
            "triggers": [],
        }
        entity = GameEntity.from_dict(data)
        assert entity.voice_profile is None
        assert entity.dialogue_lines == {}

    def test_entity_with_voice_profile_roundtrip(self):
        entity = GameEntity("Bard", "npc")
        entity.voice_profile = VoiceProfile(
            source_type="preset",
            reference_audio="seeds/barkeep.wav",
            preset_name="barkeep",
        )
        data = entity.to_dict()
        assert "voice_profile" in data

        restored = GameEntity.from_dict(data)
        assert restored.voice_profile is not None
        assert restored.voice_profile.preset_name == "barkeep"
        assert restored.voice_profile.is_voiced is True

    def test_entity_dialogue_lines_roundtrip(self):
        entity = GameEntity("Guard", "npc")
        entity.dialogue_lines = {
            "greeting": ["Halt! Who goes there?", "State your business."],
            "farewell": ["Move along."],
        }
        data = entity.to_dict()
        assert "dialogue_lines" in data

        restored = GameEntity.from_dict(data)
        assert len(restored.dialogue_lines["greeting"]) == 2
        assert restored.dialogue_lines["farewell"] == ["Move along."]

    def test_voice_profile_none_by_default(self):
        entity = GameEntity("Villager", "npc")
        assert entity.voice_profile is None
        assert entity.dialogue_lines == {}

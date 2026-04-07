"""Tests for VoiceProfile dataclass."""

from core.voice.voice_profile import VoiceProfile


class TestVoiceProfile:

    def test_defaults(self):
        vp = VoiceProfile()
        assert vp.source_type == "none"
        assert vp.is_voiced is False
        assert len(vp.voice_id) == 12

    def test_preset_is_voiced(self):
        vp = VoiceProfile(
            source_type="preset",
            reference_audio="core/audio/voice_seeds/grizzled_veteran.wav",
            preset_name="grizzled_veteran",
        )
        assert vp.is_voiced is True

    def test_none_is_not_voiced(self):
        vp = VoiceProfile(source_type="none")
        assert vp.is_voiced is False

    def test_recorded_is_voiced(self):
        vp = VoiceProfile(source_type="recorded", reference_audio="voices/hero.wav")
        assert vp.is_voiced is True

    def test_serialization_roundtrip(self):
        vp = VoiceProfile(
            source_type="preset",
            reference_audio="seeds/test.wav",
            preset_name="narrator",
            exaggeration=0.7,
            speed_factor=0.9,
            cfg_weight=0.6,
            language="fr",
            pitch_description="Deep and slow",
        )
        data = vp.to_dict()
        restored = VoiceProfile.from_dict(data)
        assert restored.source_type == "preset"
        assert restored.reference_audio == "seeds/test.wav"
        assert restored.exaggeration == 0.7
        assert restored.language == "fr"
        assert restored.voice_id == vp.voice_id

    def test_voice_id_unique(self):
        a = VoiceProfile()
        b = VoiceProfile()
        assert a.voice_id != b.voice_id

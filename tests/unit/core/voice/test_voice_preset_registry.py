"""Tests for voice preset registry."""

from core.voice.voice_preset_registry import (
    VOICE_PRESETS, get_preset, list_presets, get_presets_for_entity_type,
)
from core.voice.voice_profile import VoiceProfile


class TestVoicePresetRegistry:

    def test_presets_registered(self):
        assert len(list_presets()) >= 10

    def test_get_preset_by_id(self):
        p = get_preset("grizzled_veteran")
        assert p is not None
        assert p.name == "Grizzled Veteran"

    def test_get_preset_unknown_returns_none(self):
        assert get_preset("nonexistent") is None

    def test_preset_to_voice_profile(self):
        p = get_preset("narrator")
        vp = p.to_voice_profile()
        assert isinstance(vp, VoiceProfile)
        assert vp.preset_name == "narrator"

    def test_preset_to_voice_profile_no_seed(self):
        # Use a preset without reference audio
        p = get_preset("ethereal")
        vp = p.to_voice_profile()
        # No reference audio file -> source_type="none"
        assert vp.source_type == "none"

    def test_get_presets_for_entity_type(self):
        results = get_presets_for_entity_type("guard")
        ids = [p.preset_id for p in results]
        assert "grizzled_veteran" in ids

    def test_all_presets_have_unique_ids(self):
        ids = [p.preset_id for p in list_presets()]
        assert len(ids) == len(set(ids))

    def test_all_presets_have_descriptions(self):
        for p in list_presets():
            assert len(p.description) > 10, f"{p.preset_id} has short description"

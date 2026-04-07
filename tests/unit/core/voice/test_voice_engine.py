"""Tests for VoiceEngine (all mocked — no real model needed)."""

import pytest
from unittest.mock import patch, MagicMock

from core.voice.voice_engine import VoiceEngine, HardwareTier
from core.voice.voice_profile import VoiceProfile


@pytest.fixture(autouse=True)
def reset():
    VoiceEngine.reset_instance()
    yield
    VoiceEngine.reset_instance()


class TestSingleton:
    def test_instance_returns_same(self):
        assert VoiceEngine.instance() is VoiceEngine.instance()


class TestHardwareDetection:

    @patch.dict("sys.modules", {"chatterbox": None})
    def test_no_chatterbox_returns_none(self):
        engine = VoiceEngine()
        engine._tier = None
        with patch("builtins.__import__", side_effect=ImportError):
            tier = engine.detect_hardware()
        assert tier == HardwareTier.NONE

    def test_cached_tier(self):
        engine = VoiceEngine()
        engine._tier = HardwareTier.CPU
        assert engine.detect_hardware() == HardwareTier.CPU


class TestGenerate:

    def test_returns_none_when_unavailable(self):
        engine = VoiceEngine()
        engine._tier = HardwareTier.NONE
        result = engine.generate("Hello", VoiceProfile())
        assert result is None

    def test_unload_clears_model(self):
        engine = VoiceEngine()
        engine._model = MagicMock()
        engine.unload_model()
        assert engine._model is None

    def test_get_sample_rate(self):
        engine = VoiceEngine()
        assert engine.get_sample_rate() == 24000

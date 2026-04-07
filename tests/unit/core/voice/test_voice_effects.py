"""Tests for voice effects module."""

import numpy as np
import pytest


def _pedalboard_available() -> bool:
    try:
        import pedalboard  # noqa: F401
        return True
    except ImportError:
        return False


class TestApplyVoiceEffects:
    """Test the effects application function."""

    def _make_samples(self, duration_s=2.0, sr=24000):
        """Generate a simple sine wave for testing."""
        t = np.linspace(0, duration_s, int(sr * duration_s), dtype=np.float32)
        return np.sin(2 * np.pi * 440 * t) * 0.5

    def test_no_preset_returns_unchanged(self):
        from core.voice.voice_effects import apply_voice_effects
        samples = self._make_samples()
        result = apply_voice_effects(samples, 24000, None)
        np.testing.assert_array_equal(result, samples)

    def test_unknown_preset_returns_unchanged(self):
        from core.voice.voice_effects import apply_voice_effects
        samples = self._make_samples()
        result = apply_voice_effects(samples, 24000, "nonexistent_preset")
        np.testing.assert_array_equal(result, samples)

    @pytest.mark.skipif(
        not _pedalboard_available(),
        reason="pedalboard not installed"
    )
    def test_ethereal_modifies_audio(self):
        """Run in subprocess to avoid PyQt5/pedalboard native conflict."""
        import subprocess, sys
        result = subprocess.run([
            sys.executable, "-c",
            "import numpy as np; "
            "from core.voice.voice_effects import apply_voice_effects; "
            "s = np.sin(np.linspace(0,100,48000,dtype=np.float32))*0.5; "
            "r = apply_voice_effects(s, 24000, 'ethereal'); "
            "assert not np.array_equal(r, s), 'should modify'; "
            "assert np.abs(r).max() <= 0.95, 'should normalize'; "
            "print('OK')"
        ], capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr

    @pytest.mark.skipif(
        not _pedalboard_available(),
        reason="pedalboard not installed"
    )
    def test_warlord_modifies_audio(self):
        """Run in subprocess to avoid PyQt5/pedalboard native conflict."""
        import subprocess, sys
        result = subprocess.run([
            sys.executable, "-c",
            "import numpy as np; "
            "from core.voice.voice_effects import apply_voice_effects; "
            "s = np.sin(np.linspace(0,100,48000,dtype=np.float32))*0.5; "
            "r = apply_voice_effects(s, 24000, 'warlord'); "
            "assert not np.array_equal(r, s); "
            "print('OK')"
        ], capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr

    def test_clean_presets_return_unchanged(self):
        from core.voice.voice_effects import apply_voice_effects
        samples = self._make_samples()
        for preset in ("roguish_trickster", "young_adventurer"):
            result = apply_voice_effects(samples, 24000, preset)
            np.testing.assert_array_equal(result, samples)

    def test_graceful_without_pedalboard(self, monkeypatch):
        """If pedalboard import fails, effects are silently skipped."""
        import core.voice.voice_effects as mod
        mod._effects_chains = None
        monkeypatch.setattr(mod, "_build_effects_chains", lambda: {})
        samples = self._make_samples()
        result = mod.apply_voice_effects(samples, 24000, "ethereal")
        np.testing.assert_array_equal(result, samples)

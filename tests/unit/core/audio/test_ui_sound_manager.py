"""Tests for UISoundManager."""

import pytest
from unittest.mock import MagicMock
from pathlib import Path

from core.audio.ui_sound_manager import UISoundManager, SoundCategory, _SFX_ROOT


@pytest.fixture(autouse=True)
def reset_singleton():
    UISoundManager.reset_instance()
    yield
    UISoundManager.reset_instance()


class TestSingleton:
    def test_instance_returns_same_object(self):
        a = UISoundManager.instance()
        b = UISoundManager.instance()
        assert a is b

    def test_reset_clears_instance(self):
        a = UISoundManager.instance()
        UISoundManager.reset_instance()
        b = UISoundManager.instance()
        assert a is not b


class TestPathResolution:
    def test_resolve_tome_path(self):
        mgr = UISoundManager()
        mgr.set_theme("tome")
        path = mgr.resolve_path("click")
        assert path is not None
        assert "tome" in str(path)

    def test_resolve_stone_path(self):
        mgr = UISoundManager()
        mgr.set_theme("stone")
        path = mgr.resolve_path("click")
        assert path is not None
        assert "stone" in str(path)

    def test_shared_fallback(self):
        mgr = UISoundManager()
        mgr.set_theme("tome")
        path = mgr.resolve_path("combat_start")
        assert path is not None
        assert "shared" in str(path)

    def test_missing_returns_none(self):
        mgr = UISoundManager()
        assert mgr.resolve_path("totally_nonexistent_xyz") is None

    def test_theme_change(self):
        mgr = UISoundManager()
        mgr.set_theme("tome")
        assert mgr._active_theme == "tome"
        mgr.set_theme("stone")
        assert mgr._active_theme == "stone"


class TestVariants:
    def test_variant_discovery(self):
        mgr = UISoundManager()
        mgr.set_theme("stone")
        # attack_01.wav, attack_02.wav, attack_03.wav exist
        path = mgr.resolve_path("attack")
        assert path is not None
        assert "attack" in path.name

    def test_variant_random_distribution(self):
        mgr = UISoundManager()
        mgr.set_theme("stone")
        seen = set()
        for _ in range(30):
            path = mgr.resolve_path("attack")
            if path:
                seen.add(path.name)
        # Should see more than 1 variant
        assert len(seen) >= 2


class TestMuting:
    def test_muted_skips(self):
        mgr = UISoundManager()
        mgr.set_muted(True)
        mgr.play("click")  # Should not crash

    def test_mute_state(self):
        mgr = UISoundManager()
        assert mgr.muted is False
        mgr.set_muted(True)
        assert mgr.muted is True


class TestVolume:
    def test_set_and_get(self):
        mgr = UISoundManager()
        mgr.set_volume(SoundCategory.COMBAT, 80)
        assert mgr.get_volume(SoundCategory.COMBAT) == 80

    def test_clamps(self):
        mgr = UISoundManager()
        mgr.set_volume(SoundCategory.UI, 150)
        assert mgr.get_volume(SoundCategory.UI) == 100
        mgr.set_volume(SoundCategory.UI, -10)
        assert mgr.get_volume(SoundCategory.UI) == 0

    def test_persists(self):
        settings = MagicMock()
        mgr = UISoundManager(settings_manager=settings)
        mgr.set_volume(SoundCategory.COMBAT, 60)
        settings.set.assert_called_with("volume_combat", 60)

    def test_defaults(self):
        mgr = UISoundManager()
        assert mgr.get_volume(SoundCategory.UI) == 30
        assert mgr.get_volume(SoundCategory.COMBAT) == 50
        assert mgr.get_volume(SoundCategory.ALERT) == 70
        assert mgr.get_volume(SoundCategory.AMBIENT) == 40


class TestPlayback:
    def test_play_missing_no_crash(self):
        mgr = UISoundManager()
        mgr.play("nonexistent_12345")

    def test_play_shared_missing_no_crash(self):
        mgr = UISoundManager()
        mgr.play_shared("nonexistent_shared_12345")

    def test_play_shared_resolves_shared(self):
        mgr = UISoundManager()
        mgr.set_theme("stone")
        # play_shared should always use shared/ dir
        mgr.play_shared("your_turn")  # Should not crash

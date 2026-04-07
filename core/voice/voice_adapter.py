"""High-level adapter for all voice operations in the app.

All UI code should use VoiceAdapter instead of touching VoiceEngine,
VoiceCache, or VoiceProfile directly. This keeps the coupling in one place.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Callable, Optional

from core.voice.voice_profile import VoiceProfile

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class VoiceAdapter:
    """Single interface between UI and the voice system."""

    _instance: Optional[VoiceAdapter] = None

    @classmethod
    def instance(cls) -> VoiceAdapter:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._engine = None
        self._cache = None

    # ─── Engine access (lazy) ───────────────────────────────────

    def _get_engine(self):
        if self._engine is None:
            try:
                from core.voice.voice_engine import VoiceEngine
                self._engine = VoiceEngine.instance()
            except Exception:
                pass
        return self._engine

    def _get_cache(self):
        if self._cache is None:
            try:
                from core.voice.voice_cache import VoiceCache
                cache_dir = _PROJECT_ROOT / "assets" / "voice_cache"
                self._cache = VoiceCache(cache_dir)
            except Exception:
                pass
        return self._cache

    # ─── Status ─────────────────────────────────────────────────

    def is_available(self) -> bool:
        """True if Chatterbox is installed and hardware is usable."""
        engine = self._get_engine()
        if not engine:
            return False
        from core.voice.voice_engine import HardwareTier
        return engine.detect_hardware() != HardwareTier.NONE

    def hardware_tier(self) -> str:
        """Return 'gpu', 'cpu', or 'none'."""
        engine = self._get_engine()
        if not engine:
            return "none"
        return engine.detect_hardware().value

    def is_model_loaded(self) -> bool:
        engine = self._get_engine()
        return engine is not None and engine._model is not None

    def load_model(
        self, on_progress: Callable[[str, float], None] | None = None
    ) -> bool:
        engine = self._get_engine()
        if not engine:
            return False
        return engine.load_model(on_progress)

    # ─── Presets ────────────────────────────────────────────────

    def list_presets(self) -> list:
        """Return all registered voice presets."""
        try:
            from core.voice.voice_preset_registry import VOICE_PRESETS
            return list(VOICE_PRESETS.values())
        except ImportError:
            return []

    def get_preset(self, name: str):
        """Get a preset by ID, or None."""
        try:
            from core.voice.voice_preset_registry import get_preset
            return get_preset(name)
        except (ImportError, KeyError):
            return None

    # ─── Profile management ─────────────────────────────────────

    def create_profile(
        self, preset_name: str = "", **overrides
    ) -> VoiceProfile:
        """Create a VoiceProfile from a preset with optional overrides."""
        preset = self.get_preset(preset_name) if preset_name else None
        if preset:
            profile = preset.to_voice_profile()
            for key, val in overrides.items():
                if hasattr(profile, key):
                    setattr(profile, key, val)
            return profile
        return VoiceProfile(**overrides)

    def profile_from_recording(self, wav_path: str) -> VoiceProfile:
        """Create a VoiceProfile from a recorded/uploaded audio file."""
        return VoiceProfile(
            source_type="recorded",
            reference_audio=wav_path,
            pitch_description=f"Custom recording: {Path(wav_path).name}",
        )

    @staticmethod
    def recording_path(entity_name: str) -> Path:
        """Return the standard save path for a voice recording.

        Creates the parent directory if it doesn't exist.
        """
        slug = re.sub(r"[^a-zA-Z0-9_-]", "_", entity_name).lower()
        path = Path("assets/voice_recordings") / f"{slug}.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    # ─── Generation ─────────────────────────────────────────────

    def preview(self, text: str, profile: VoiceProfile) -> bytes | None:
        """Generate a short preview. Returns WAV bytes or None."""
        engine = self._get_engine()
        if not engine:
            return None
        if not self.is_model_loaded():
            if not self.load_model():
                return None

        ref_path = None
        if profile.reference_audio:
            p = Path(profile.reference_audio)
            if not p.is_absolute():
                p = _PROJECT_ROOT / p
            if p.exists():
                ref_path = p

        return engine.generate(text, profile, ref_path)

    def generate(self, text: str, profile: VoiceProfile) -> bytes | None:
        """Generate audio and cache it. Returns WAV bytes or None."""
        cache = self._get_cache()

        # Check cache first
        if cache:
            from core.voice.voice_cache import VoiceCache
            key = VoiceCache.compute_cache_key(
                profile.voice_id, text,
                profile.exaggeration, profile.speed_factor, profile.cfg_weight,
            )
            cached = cache.get(key)
            if cached:
                return Path(cached).read_bytes()

        audio = self.preview(text, profile)

        # Cache the result
        if audio and cache:
            cache.put(key, audio, "", text)

        return audio

    def generate_batch(
        self,
        lines: list[str],
        profile: VoiceProfile,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[bytes | None]:
        """Generate multiple lines. Calls on_progress(current, total)."""
        results = []
        for i, text in enumerate(lines):
            audio = self.generate(text, profile)
            results.append(audio)
            if on_progress:
                on_progress(i + 1, len(lines))
        return results

    # ─── Cache ──────────────────────────────────────────────────

    def cache_stats(self) -> dict:
        cache = self._get_cache()
        if cache:
            return cache.get_stats()
        return {"entries": 0, "size_mb": 0}

    def clear_cache(self) -> None:
        cache = self._get_cache()
        if cache:
            cache.clear_all()

    def is_cached(self, text: str, profile: VoiceProfile) -> bool:
        cache = self._get_cache()
        if not cache:
            return False
        from core.voice.voice_cache import VoiceCache
        key = VoiceCache.compute_cache_key(
            profile.voice_id, text,
            profile.exaggeration, profile.speed_factor, profile.cfg_weight,
        )
        return cache.has(key)

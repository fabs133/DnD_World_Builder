"""Themed UI sound effect manager.

Plays short feedback sounds for UI events with theme-aware path
resolution and per-category volume control.  Extends the existing
:class:`~core.audio_player.AudioPlayer` pattern as a singleton.
"""

from __future__ import annotations

import logging
import random
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

_SFX_ROOT = Path(__file__).parent / "sfx"


class SoundCategory(Enum):
    UI = "ui"
    COMBAT = "combat"
    ALERT = "alert"
    AMBIENT = "ambient"


_DEFAULT_VOLUMES = {
    SoundCategory.UI: 30,
    SoundCategory.COMBAT: 50,
    SoundCategory.ALERT: 70,
    SoundCategory.AMBIENT: 40,
}


class UISoundManager:
    """Singleton manager for themed UI sound effects.

    Sound assets live in ``core/audio/sfx/{tome,stone,shared}/``.
    The active theme determines which directory is searched first.
    Falls back to ``shared/`` if not found in the theme directory.

    Handles missing files gracefully (warns, no crash).
    """

    _instance: Optional[UISoundManager] = None

    @classmethod
    def instance(cls) -> UISoundManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None

    def __init__(self, settings_manager: Any = None):
        self._settings = settings_manager
        self._active_theme = "tome"
        self._muted = False
        self._volumes: dict[SoundCategory, int] = dict(_DEFAULT_VOLUMES)
        self._player = None  # Lazy QSoundEffect / fallback

        # Load persisted volumes from settings
        if settings_manager:
            for cat in SoundCategory:
                key = f"volume_{cat.value}"
                val = settings_manager.get(key)
                if val is not None:
                    self._volumes[cat] = max(0, min(100, int(val)))
            self._muted = bool(settings_manager.get("sound_muted", False))

    def set_theme(self, theme: str) -> None:
        """Swap the active sound theme (``"tome"`` or ``"stone"``)."""
        self._active_theme = theme

    def set_volume(self, category: SoundCategory, volume: int) -> None:
        """Set volume (0-100) for a category. Persists to settings."""
        volume = max(0, min(100, volume))
        self._volumes[category] = volume
        if self._settings:
            self._settings.set(f"volume_{category.value}", volume)

    def get_volume(self, category: SoundCategory) -> int:
        return self._volumes.get(category, 50)

    def set_muted(self, muted: bool) -> None:
        self._muted = muted
        if self._settings:
            self._settings.set("sound_muted", muted)

    @property
    def muted(self) -> bool:
        return self._muted

    def resolve_path(self, sound_id: str) -> Path | None:
        """Resolve a sound_id to a file path.

        Searches theme dir first, then shared/. Supports variants
        (e.g., ``attack_01.wav``, ``attack_02.wav`` — picks randomly).
        """
        # Check theme directory
        result = self._resolve_in_dir(_SFX_ROOT / self._active_theme, sound_id)
        if result:
            return result
        # Fallback to shared
        return self._resolve_in_dir(_SFX_ROOT / "shared", sound_id)

    def _resolve_in_dir(self, directory: Path, sound_id: str) -> Path | None:
        """Resolve a sound in a specific directory, with variant support.

        Supports hierarchical IDs like ``"attacks/sword/hit"`` which maps
        to ``directory/attacks/sword/hit.wav`` or
        ``directory/attacks/sword/hit_01.wav`` (random variant).
        """
        # The sound_id may contain '/' for subdirectory paths
        parts = sound_id.replace("\\", "/").split("/")
        base_name = parts[-1]
        sub_dir = directory.joinpath(*parts[:-1]) if len(parts) > 1 else directory

        # Try common audio extensions
        for ext in (".wav", ".ogg", ".mp3"):
            exact = sub_dir / f"{base_name}{ext}"
            if exact.exists():
                return exact
        # Check for numbered variants: {base}_01.wav, {base}_02.wav, ...
        variants = self._get_variants(base_name, sub_dir)
        if variants:
            return random.choice(variants)
        # Check for any .wav files in the subdirectory (match by prefix)
        if sub_dir.exists():
            prefix_matches = sorted(sub_dir.glob(f"{base_name}*.wav"))
            if prefix_matches:
                return random.choice(prefix_matches)
        return None

    def _get_variants(self, sound_id: str, directory: Path) -> List[Path]:
        """Find all variant files matching {sound_id}_NN.{ext} or {sound_id}*.{ext}."""
        if not directory.exists():
            return []
        results = []
        for ext in ("wav", "ogg", "mp3"):
            strict = sorted(directory.glob(f"{sound_id}_[0-9][0-9].{ext}"))
            if strict:
                results.extend(strict)
        if results:
            return results
        # Broader match for any naming style
        for ext in ("wav", "ogg", "mp3"):
            results.extend(sorted(directory.glob(f"{sound_id}*.{ext}")))
        return results

    def play(
        self,
        sound_id: str,
        category: SoundCategory = SoundCategory.UI,
    ) -> None:
        """Play a sound by ID from the active theme directory.

        :param sound_id: Sound identifier (filename without extension).
        :param category: Volume channel to use.
        """
        if self._muted:
            return

        path = self.resolve_path(sound_id)
        if path is None:
            logger.warning(f"Sound '{sound_id}' not found in theme '{self._active_theme}' or shared")
            return

        volume = self._volumes.get(category, 50) / 100.0
        self._play_file(path, volume, category)

    def play_shared(
        self,
        sound_id: str,
        category: SoundCategory = SoundCategory.ALERT,
    ) -> None:
        """Play from shared/ directory regardless of active theme."""
        if self._muted:
            return

        path = _SFX_ROOT / "shared" / f"{sound_id}.wav"
        if not path.exists():
            logger.warning(f"Shared sound '{sound_id}' not found")
            return

        volume = self._volumes.get(category, 50) / 100.0
        self._play_file(path, volume, category)

    def _play_file(
        self,
        path: Path,
        volume: float,
        category: SoundCategory = SoundCategory.UI,
    ) -> None:
        """Play a .wav file, routing through AudioMixer when available."""
        try:
            from core.audio.audio_mixer import AudioMixer, AudioChannel

            _CATEGORY_TO_CHANNEL = {
                SoundCategory.UI: AudioChannel.UI,
                SoundCategory.COMBAT: AudioChannel.SFX,
                SoundCategory.ALERT: AudioChannel.SFX,
                SoundCategory.AMBIENT: AudioChannel.AMBIENT,
            }

            mixer = AudioMixer.instance()
            if mixer:
                channel = _CATEGORY_TO_CHANNEL.get(category, AudioChannel.SFX)
                mixer.play(str(path), channel)
                return
        except Exception:
            pass
        # Fallback to legacy single-player
        try:
            from core.audio_player import AudioPlayer
            AudioPlayer.instance().play(str(path))
        except Exception as e:
            logger.warning(f"Failed to play {path}: {e}")

    # ── Ambient audio loop ──────────────────────────────────────

    def play_ambient(self, sound_id: str) -> None:
        """Play ambient audio in a loop. Stops any current ambient."""
        if self._muted:
            return
        # Try multiple audio formats (mp3 first — most reliable on Windows)
        ambient_path = None
        for ext in (".mp3", ".wav", ".ogg"):
            candidate = _SFX_ROOT / "ambient" / f"{sound_id}{ext}"
            if candidate.exists():
                ambient_path = candidate
                break
        if not ambient_path:
            logger.warning(f"Ambient '{sound_id}' not found")
            return
        if hasattr(self, "_current_ambient") and self._current_ambient == sound_id:
            return  # Already playing this ambient

        was_playing = hasattr(self, "_current_ambient") and self._current_ambient
        self._current_ambient = sound_id

        # Prefer AudioMixer: crossfade if already playing, otherwise start fresh
        try:
            from core.audio.audio_mixer import AudioMixer, AudioChannel
            mixer = AudioMixer.instance()
            if mixer:
                path_str = str(ambient_path.resolve())
                if was_playing:
                    mixer.crossfade_ambient(path_str, duration_ms=1500)
                else:
                    mixer.play_looped(path_str, AudioChannel.AMBIENT)
                logger.info(f"Ambient: {'crossfade' if was_playing else 'start'} '{sound_id}'")
                return
        except Exception:
            pass

        self.stop_ambient()

        # Fallback to legacy ambient player
        try:
            from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
            from PyQt5.QtCore import QUrl
            if not hasattr(self, "_ambient_player"):
                self._ambient_player = QMediaPlayer()
            playlist = QMediaPlaylist()
            playlist.addMedia(QMediaContent(QUrl.fromLocalFile(str(ambient_path.resolve()))))
            playlist.setPlaybackMode(QMediaPlaylist.Loop)
            self._ambient_player.setPlaylist(playlist)
            volume = self._volumes.get(SoundCategory.AMBIENT, 40)
            self._ambient_player.setVolume(volume)
            self._ambient_player.play()
            logger.info(f"Ambient: playing '{sound_id}' (loop, vol={volume})")
        except ImportError:
            logger.warning("QtMultimedia not available for ambient audio")
        except Exception as e:
            logger.warning(f"Ambient playback failed: {e}")

    def stop_ambient(self) -> None:
        """Stop current ambient audio loop."""
        self._current_ambient = ""
        # Stop mixer ambient
        try:
            from core.audio.audio_mixer import AudioMixer, AudioChannel
            mixer = AudioMixer.instance()
            if mixer:
                mixer.stop(AudioChannel.AMBIENT)
        except Exception:
            pass
        # Always stop legacy player too (may have been started by fallback path)
        if hasattr(self, "_ambient_player"):
            try:
                self._ambient_player.stop()
            except Exception:
                pass

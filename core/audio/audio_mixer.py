"""Multi-channel audio mixer — thin facade over ViewDispatcher.

All public methods return instantly.  The actual QMediaPlayer work
runs on a persistent AudioWorker thread managed by ViewDispatcher.
The GUI thread never touches QMediaPlayer.

Backward-compatible API: callers use ``AudioMixer.instance().play()``
exactly as before, but no blocking occurs.
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

try:
    from PyQt5.QtCore import QObject

    _HAS_QT = True
except ImportError:
    _HAS_QT = False

    class QObject:  # type: ignore[no-redef]
        def __init__(self, *a, **kw):
            pass


class AudioChannel(Enum):
    """Logical audio channels with independent playback."""

    AMBIENT = "ambient"
    SFX = "sfx"
    VOICE = "voice"
    UI = "ui"
    MUSIC = "music"


_DEFAULT_CHANNEL_VOLUMES: Dict[AudioChannel, int] = {
    AudioChannel.AMBIENT: 40,
    AudioChannel.SFX: 50,
    AudioChannel.VOICE: 80,
    AudioChannel.UI: 30,
    AudioChannel.MUSIC: 50,
}


class AudioMixer(QObject):
    """Non-blocking audio facade.

    Every call is translated into an :class:`Effect` and dispatched
    to the :class:`ViewDispatcher`, which hands it to a persistent
    :class:`AudioWorker` thread.  If no dispatcher is available yet
    (e.g. during early startup or tests), calls are silently dropped.
    """

    _instance: Optional["AudioMixer"] = None

    @classmethod
    def instance(cls) -> Optional["AudioMixer"]:
        """Return the global mixer (set during app startup)."""
        return cls._instance

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._muted = False
        self._volumes: Dict[AudioChannel, int] = dict(_DEFAULT_CHANNEL_VOLUMES)

    # ------------------------------------------------------------------
    # Internal: dispatch helper
    # ------------------------------------------------------------------

    def _dispatch(self, action: str, **params) -> None:
        """Send an Effect to the ViewDispatcher (non-blocking)."""
        try:
            from core.view_dispatcher import ViewDispatcher, Effect, EffectType

            vd = ViewDispatcher.instance()
            if vd is None:
                return
            vd.dispatch(Effect(
                effect_type=EffectType.AUDIO,
                action=action,
                params=params,
            ))
        except Exception:
            logger.debug("[AudioMixer] Dispatch unavailable for %s", action)

    # ------------------------------------------------------------------
    # Public API (all non-blocking)
    # ------------------------------------------------------------------

    def play(
        self,
        file_path: str | Path,
        channel: AudioChannel = AudioChannel.SFX,
    ) -> None:
        """Play a sound on the specified channel (non-blocking)."""
        if self._muted:
            return
        path_str = str(Path(file_path).resolve()) if file_path else ""
        if not path_str:
            return
        self._dispatch("play", path=path_str, channel=channel.value)

    def play_looped(
        self,
        file_path: str | Path,
        channel: AudioChannel = AudioChannel.AMBIENT,
    ) -> None:
        """Play audio in a loop on the specified channel (non-blocking)."""
        if self._muted:
            return
        path_str = str(Path(file_path).resolve()) if file_path else ""
        if not path_str:
            return
        self._dispatch("play_looped", path=path_str, channel=channel.value)

    def stop(self, channel: AudioChannel) -> None:
        """Stop playback on a specific channel."""
        self._dispatch("stop", channel=channel.value)

    def stop_all(self) -> None:
        """Stop all channels."""
        self._dispatch("stop_all")

    def set_volume(self, channel: AudioChannel, volume: int) -> None:
        """Set volume (0-100) for a channel."""
        volume = max(0, min(100, volume))
        self._volumes[channel] = volume
        self._dispatch("set_volume", channel=channel.value, volume=volume)

    def get_volume(self, channel: AudioChannel) -> int:
        return self._volumes.get(channel, 50)

    def set_muted(self, muted: bool) -> None:
        self._muted = muted
        self._dispatch("set_muted", muted=muted)

    @property
    def muted(self) -> bool:
        return self._muted

    def crossfade_ambient(
        self,
        new_path: str | Path,
        duration_ms: int = 2000,
    ) -> None:
        """Crossfade from current ambient to a new track (non-blocking)."""
        if self._muted:
            return
        path_str = str(Path(new_path).resolve()) if new_path else ""
        if not path_str:
            return
        self._dispatch(
            "crossfade_ambient",
            path=path_str,
            duration_ms=duration_ms,
        )

"""Audio worker that owns QMediaPlayer instances on a dedicated thread.

All blocking media operations (setMedia, play, stop) happen here,
completely off the GUI thread.  The ViewDispatcher hands ``Effect``
objects to this worker via its thread-safe queue.

The worker creates its own QMediaPlayer pool when it starts on the
worker thread (ensuring correct thread affinity).
"""

from __future__ import annotations

import logging
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer, QMediaPlaylist
    from PyQt5.QtCore import QObject, QTimer, QUrl, pyqtSlot

    _HAS_MULTIMEDIA = True
except ImportError:
    _HAS_MULTIMEDIA = False
    QObject = object  # type: ignore[assignment,misc]

    def pyqtSlot(*a, **kw):  # type: ignore[no-redef]
        def _dec(fn):
            return fn
        return _dec


class AudioWorker(QObject):
    """Processes audio effects on a dedicated thread.

    Player instances are created lazily on the first ``_handle_effect``
    call, which runs on the worker thread — guaranteeing correct
    Qt thread affinity.

    Supports the same channel/pool model as AudioMixer but without
    any GUI-thread involvement.
    """

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._effect_queue: deque = deque()
        self._initialized = False
        self._muted = False

        # Player pools (created on worker thread)
        self._sfx_pool: List = []
        self._sfx_idx = 0
        self._ui_pool: List = []
        self._ui_idx = 0
        self._ambient: Optional[QMediaPlayer] = None
        self._voice: Optional[QMediaPlayer] = None
        self._music: Optional[QMediaPlayer] = None

        self._volumes: Dict[str, int] = {
            "ambient": 40,
            "sfx": 50,
            "voice": 80,
            "ui": 30,
            "music": 50,
        }

        # Ducking state
        self._ducking = False
        self._duck_restore_volume = 0
        self._duck_timer: Optional[QTimer] = None

    # ------------------------------------------------------------------
    # Lazy init (runs on worker thread)
    # ------------------------------------------------------------------

    def _ensure_initialized(self) -> None:
        if self._initialized or not _HAS_MULTIMEDIA:
            return
        self._sfx_pool = [self._make_player(f"sfx-{i}") for i in range(4)]
        self._ui_pool = [self._make_player(f"ui-{i}") for i in range(2)]
        self._ambient = self._make_player("ambient")
        self._voice = self._make_player("voice")
        self._music = self._make_player("music")
        self._initialized = True
        logger.info("[AudioWorker] Initialized %d players on worker thread", 9)

    def _make_player(self, label: str) -> QMediaPlayer:
        player = QMediaPlayer(self)
        player.error.connect(
            lambda err, p=player, lbl=label: logger.warning(
                "[AudioWorker] %s error: %s", lbl, p.errorString()
            )
        )
        return player

    # ------------------------------------------------------------------
    # Cleanup (called on worker thread before shutdown)
    # ------------------------------------------------------------------

    @pyqtSlot()
    def cleanup(self) -> None:
        """Stop all timers and players. Must be called on the worker thread."""
        if self._duck_timer is not None:
            self._duck_timer.stop()
            self._duck_timer = None
        if hasattr(self, "_fade_timer") and self._fade_timer is not None:
            self._fade_timer.stop()
            self._fade_timer = None
        self._do_stop_all()

    # ------------------------------------------------------------------
    # Effect processing (called via ViewDispatcher on worker thread)
    # ------------------------------------------------------------------

    @pyqtSlot()
    def _handle_effect(self) -> None:
        """Drain the effect queue (invoked by ViewDispatcher)."""
        self._ensure_initialized()
        while self._effect_queue:
            effect = self._effect_queue.popleft()
            try:
                self._process(effect)
            except Exception:
                logger.exception(
                    "[AudioWorker] Error processing %s", effect.action
                )

    def _process(self, effect) -> None:
        action = effect.action
        params = effect.params

        if action == "play":
            self._do_play(
                params.get("path", ""),
                params.get("channel", "sfx"),
            )
        elif action == "play_looped":
            self._do_play_looped(
                params.get("path", ""),
                params.get("channel", "ambient"),
            )
        elif action == "stop":
            self._do_stop(params.get("channel", "sfx"))
        elif action == "stop_all":
            self._do_stop_all()
        elif action == "set_volume":
            ch = params.get("channel", "sfx")
            vol = params.get("volume", 50)
            self._volumes[ch] = max(0, min(100, vol))
        elif action == "set_muted":
            self._muted = params.get("muted", False)
            if self._muted:
                self._do_stop_all()
        elif action == "crossfade_ambient":
            self._do_crossfade(
                params.get("path", ""),
                params.get("duration_ms", 2000),
            )
        else:
            logger.warning("[AudioWorker] Unknown action: %s", action)

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def _do_play(self, file_path: str, channel: str) -> None:
        if not _HAS_MULTIMEDIA or self._muted or not file_path:
            return

        path = Path(file_path)
        if not path.exists():
            logger.warning("[AudioWorker] File not found: %s", file_path)
            return

        player = self._get_player(channel)
        if player is None:
            return

        volume = self._volumes.get(channel, 50)
        player.setVolume(volume)
        player.setMedia(QMediaContent(QUrl.fromLocalFile(str(path.resolve()))))
        player.play()

        # Duck ambient when SFX plays
        if channel == "sfx":
            self._duck_ambient()

    def _do_play_looped(self, file_path: str, channel: str) -> None:
        if not _HAS_MULTIMEDIA or self._muted or not file_path:
            return

        path = Path(file_path)
        if not path.exists():
            logger.warning("[AudioWorker] Loop file not found: %s", file_path)
            return

        player = self._get_dedicated(channel)
        if player is None:
            return

        # Clean up old playlist
        player.stop()
        old_playlist = player.playlist()
        if old_playlist is not None:
            player.setPlaylist(None)
            old_playlist.deleteLater()

        playlist = QMediaPlaylist(player)
        playlist.addMedia(QMediaContent(QUrl.fromLocalFile(str(path.resolve()))))
        playlist.setPlaybackMode(QMediaPlaylist.Loop)
        player.setPlaylist(playlist)
        player.setVolume(self._volumes.get(channel, 50))
        player.play()
        logger.info("[AudioWorker] Looping on %s: %s", channel, file_path)

    def _do_stop(self, channel: str) -> None:
        if not _HAS_MULTIMEDIA:
            return
        if channel == "sfx":
            for p in self._sfx_pool:
                p.stop()
        elif channel == "ui":
            for p in self._ui_pool:
                p.stop()
        else:
            player = self._get_dedicated(channel)
            if player:
                player.stop()

    def _do_stop_all(self) -> None:
        if not _HAS_MULTIMEDIA:
            return
        for ch in ("sfx", "ui", "ambient", "voice", "music"):
            self._do_stop(ch)

    # ------------------------------------------------------------------
    # Player selection
    # ------------------------------------------------------------------

    def _get_player(self, channel: str) -> Optional[QMediaPlayer]:
        if channel == "sfx":
            if not self._sfx_pool:
                return None
            p = self._sfx_pool[self._sfx_idx % len(self._sfx_pool)]
            self._sfx_idx += 1
            return p
        if channel == "ui":
            if not self._ui_pool:
                return None
            p = self._ui_pool[self._ui_idx % len(self._ui_pool)]
            self._ui_idx += 1
            return p
        return self._get_dedicated(channel)

    def _get_dedicated(self, channel: str) -> Optional[QMediaPlayer]:
        if channel == "ambient":
            return self._ambient
        if channel == "voice":
            return self._voice
        if channel == "music":
            return self._music
        return None

    # ------------------------------------------------------------------
    # Ambient ducking
    # ------------------------------------------------------------------

    def _duck_ambient(self) -> None:
        if self._ambient is None:
            return
        if self._ambient.state() != QMediaPlayer.PlayingState:
            return

        if self._ducking:
            if self._duck_timer is not None:
                self._duck_timer.stop()
                self._duck_timer.start(800)
            return

        self._ducking = True
        self._duck_restore_volume = self._ambient.volume()
        self._ambient.setVolume(int(self._duck_restore_volume * 0.3))

        self._duck_timer = QTimer(self)
        self._duck_timer.setSingleShot(True)
        self._duck_timer.timeout.connect(self._restore_ambient)
        self._duck_timer.start(800)

    @pyqtSlot()
    def _restore_ambient(self) -> None:
        if self._ambient is not None and self._ducking:
            self._ambient.setVolume(self._duck_restore_volume)
        self._ducking = False

    # ------------------------------------------------------------------
    # Ambient crossfade
    # ------------------------------------------------------------------

    def _do_crossfade(self, file_path: str, duration_ms: int = 2000) -> None:
        if not _HAS_MULTIMEDIA or self._ambient is None:
            self._do_play_looped(file_path, "ambient")
            return

        if self._ambient.state() != QMediaPlayer.PlayingState:
            self._do_play_looped(file_path, "ambient")
            return

        # Stop any in-progress crossfade
        if hasattr(self, "_fade_timer") and self._fade_timer is not None:
            self._fade_timer.stop()
            self._fade_timer.deleteLater()
            self._fade_timer = None

        self._fade_target = str(Path(file_path).resolve())
        self._fade_steps_total = 20
        self._fade_step = 0
        self._fade_interval = max(1, duration_ms // (2 * self._fade_steps_total))
        self._fade_original_vol = self._ambient.volume()
        self._fade_out = True

        self._fade_timer = QTimer(self)
        self._fade_timer.timeout.connect(self._fade_tick)
        self._fade_timer.start(self._fade_interval)

    @pyqtSlot()
    def _fade_tick(self) -> None:
        self._fade_step += 1
        progress = self._fade_step / self._fade_steps_total

        if self._fade_out:
            vol = int(self._fade_original_vol * (1.0 - progress))
            self._ambient.setVolume(max(0, vol))
            if self._fade_step >= self._fade_steps_total:
                self._ambient.stop()
                self._do_play_looped(self._fade_target, "ambient")
                self._ambient.setVolume(0)
                self._fade_step = 0
                self._fade_out = False
        else:
            vol = int(self._fade_original_vol * progress)
            self._ambient.setVolume(min(self._fade_original_vol, vol))
            if self._fade_step >= self._fade_steps_total:
                self._ambient.setVolume(self._fade_original_vol)
                self._fade_timer.stop()

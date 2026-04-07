"""Inline voice recorder widget for capturing reference audio.

Uses ``sounddevice`` to record from the microphone and saves to WAV.
The recorded audio can be used as a Chatterbox TTS reference voice.
"""

from __future__ import annotations

import struct
import wave
from pathlib import Path
from typing import Optional

import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox,
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal

from core.logger import app_logger

_SAMPLE_RATE = 24_000   # Match Chatterbox expected rate
_CHANNELS = 1
_MAX_DURATION = 10.0    # seconds
_MIN_DURATION = 0.5     # reject very short recordings


# ── Recording thread ────────────────────────────────────────────────


class _RecordWorker(QThread):
    """Background thread that captures audio via sounddevice."""

    duration_update = pyqtSignal(float)   # elapsed seconds
    finished = pyqtSignal(np.ndarray)     # complete audio buffer
    error = pyqtSignal(str)

    def __init__(self, device_index: Optional[int] = None, parent=None):
        super().__init__(parent)
        self._device = device_index
        self._running = False

    def run(self) -> None:
        try:
            import sounddevice as sd
        except ImportError:
            self.error.emit(
                "sounddevice is not installed. "
                "Install it with:  pip install sounddevice"
            )
            return

        chunks: list[np.ndarray] = []
        self._running = True
        elapsed = 0.0
        block_dur = 0.1  # 100 ms per callback block

        try:
            with sd.InputStream(
                samplerate=_SAMPLE_RATE,
                channels=_CHANNELS,
                dtype="float32",
                device=self._device,
                blocksize=int(_SAMPLE_RATE * block_dur),
            ) as stream:
                while self._running and elapsed < _MAX_DURATION:
                    data, _ = stream.read(int(_SAMPLE_RATE * block_dur))
                    chunks.append(data.copy())
                    elapsed += block_dur
                    self.duration_update.emit(elapsed)
        except Exception as exc:
            self.error.emit(str(exc))
            return

        if chunks:
            audio = np.concatenate(chunks, axis=0)
            self.finished.emit(audio)
        else:
            self.error.emit("No audio captured")

    def stop_recording(self) -> None:
        self._running = False


# ── Public widget ───────────────────────────────────────────────────


class VoiceRecorderWidget(QWidget):
    """Compact recording panel for voice reference capture.

    Signals:
        recording_saved(str): Emitted with the WAV file path after save.
        recording_cleared(): Emitted when the user clears the recording.
    """

    recording_saved = pyqtSignal(str)
    recording_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[_RecordWorker] = None
        self._audio: Optional[np.ndarray] = None
        self._save_path: Optional[Path] = None
        self._elapsed = 0.0

        self._build_ui()
        self._set_state("idle")

    # ── UI ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        # Device selector
        dev_row = QHBoxLayout()
        dev_row.addWidget(QLabel("Mic:"))
        self._device_combo = QComboBox()
        self._refresh_devices()
        dev_row.addWidget(self._device_combo, stretch=1)
        refresh_btn = QPushButton("\u21bb")  # ↻
        refresh_btn.setFixedWidth(24)
        refresh_btn.setToolTip("Refresh device list")
        refresh_btn.clicked.connect(self._refresh_devices)
        dev_row.addWidget(refresh_btn)
        layout.addLayout(dev_row)

        # Record / Stop
        btn_row = QHBoxLayout()
        self._record_btn = QPushButton("\u25cf Record")  # ●
        self._record_btn.setStyleSheet(
            "QPushButton { font-weight: bold; }"
            "QPushButton:hover { color: #e03030; }"
        )
        self._record_btn.clicked.connect(self._on_record)
        btn_row.addWidget(self._record_btn)

        self._stop_btn = QPushButton("\u25a0 Stop")  # ■
        self._stop_btn.clicked.connect(self._on_stop)
        btn_row.addWidget(self._stop_btn)
        layout.addLayout(btn_row)

        # Duration
        self._duration_label = QLabel("Duration: 0.0s")
        self._duration_label.setStyleSheet("color: #aaa; font-size: 10px;")
        layout.addWidget(self._duration_label)

        # Play / Clear
        play_row = QHBoxLayout()
        self._play_btn = QPushButton("\u25b6 Play")  # ▶
        self._play_btn.clicked.connect(self._on_play)
        play_row.addWidget(self._play_btn)

        self._clear_btn = QPushButton("\u2715 Clear")  # ✕
        self._clear_btn.clicked.connect(self._on_clear)
        play_row.addWidget(self._clear_btn)
        layout.addLayout(play_row)

        # Status
        self._status = QLabel("Ready to record")
        self._status.setStyleSheet("color: #888; font-size: 10px;")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

    # ── Device enumeration ──────────────────────────────────────────

    def _refresh_devices(self) -> None:
        self._device_combo.clear()
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if dev["max_input_channels"] > 0:
                    self._device_combo.addItem(dev["name"], i)
            if self._device_combo.count() == 0:
                self._device_combo.addItem("(no input devices)", None)
        except ImportError:
            self._device_combo.addItem("(sounddevice not installed)", None)
        except Exception as exc:
            self._device_combo.addItem(f"(error: {exc})", None)

    # ── State management ────────────────────────────────────────────

    def _set_state(self, state: str) -> None:
        is_idle = state == "idle"
        is_recording = state == "recording"
        has_audio = state == "has_audio"

        self._record_btn.setEnabled(is_idle or has_audio)
        self._stop_btn.setEnabled(is_recording)
        self._play_btn.setEnabled(has_audio)
        self._clear_btn.setEnabled(has_audio)
        self._device_combo.setEnabled(not is_recording)

    # ── Recording ───────────────────────────────────────────────────

    def _on_record(self) -> None:
        device_data = self._device_combo.currentData()
        if device_data is None:
            self._status.setText("No microphone available")
            return

        self._audio = None
        self._elapsed = 0.0
        self._duration_label.setText("Duration: 0.0s")
        self._status.setText("Recording...")
        self._status.setStyleSheet("color: #e03030; font-size: 10px;")
        self._set_state("recording")

        self._worker = _RecordWorker(device_index=int(device_data))
        self._worker.duration_update.connect(self._on_duration)
        self._worker.finished.connect(self._on_record_finished)
        self._worker.error.connect(self._on_record_error)
        self._worker.start()

    def _on_stop(self) -> None:
        if self._worker:
            self._worker.stop_recording()

    def _on_duration(self, elapsed: float) -> None:
        self._elapsed = elapsed
        self._duration_label.setText(f"Duration: {elapsed:.1f}s / {_MAX_DURATION:.0f}s max")

    def _on_record_finished(self, audio: np.ndarray) -> None:
        self._status.setStyleSheet("color: #888; font-size: 10px;")
        duration = len(audio) / _SAMPLE_RATE

        if duration < _MIN_DURATION:
            self._status.setText(
                f"Recording too short ({duration:.1f}s). Need at least {_MIN_DURATION}s."
            )
            self._set_state("idle")
            return

        self._audio = audio
        self._status.setText(f"Recorded {duration:.1f}s of audio")
        self._set_state("has_audio")

    def _on_record_error(self, message: str) -> None:
        self._status.setStyleSheet("color: #888; font-size: 10px;")
        self._status.setText(f"Error: {message}")
        self._set_state("idle")
        app_logger.error(f"[VoiceRecorder] {message}")

    # ── Playback ────────────────────────────────────────────────────

    def _on_play(self) -> None:
        if self._save_path and self._save_path.exists():
            from core.audio_player import AudioPlayer
            AudioPlayer.instance().play(str(self._save_path))
        elif self._audio is not None:
            # Save to temp and play
            path = self._save_to_temp()
            if path:
                from core.audio_player import AudioPlayer
                AudioPlayer.instance().play(str(path))

    def _on_clear(self) -> None:
        from core.audio_player import AudioPlayer
        AudioPlayer.instance().stop()
        self._audio = None
        self._save_path = None
        self._elapsed = 0.0
        self._duration_label.setText("Duration: 0.0s")
        self._status.setText("Ready to record")
        self._set_state("idle")
        self.recording_cleared.emit()

    # ── Saving ──────────────────────────────────────────────────────

    def save_recording(self, path: Path) -> bool:
        """Save the current recording to *path* as 16-bit PCM WAV.

        Returns True on success. Emits ``recording_saved`` signal.
        """
        if self._audio is None:
            return False

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            samples = (self._audio.flatten() * 32767).astype(np.int16)
            with wave.open(str(path), "wb") as wf:
                wf.setnchannels(_CHANNELS)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(_SAMPLE_RATE)
                wf.writeframes(samples.tobytes())

            self._save_path = path
            self._status.setText(f"Saved: {path.name}")
            self.recording_saved.emit(str(path))
            app_logger.info(f"[VoiceRecorder] Saved recording to {path}")
            return True
        except Exception as exc:
            self._status.setText(f"Save failed: {exc}")
            app_logger.error(f"[VoiceRecorder] Save failed: {exc}")
            return False

    def _save_to_temp(self) -> Optional[Path]:
        """Save to a temporary file for preview playback."""
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".wav"))
        if self.save_recording(tmp):
            return tmp
        return None

    # ── External API ────────────────────────────────────────────────

    def has_recording(self) -> bool:
        return self._audio is not None

    def saved_path(self) -> Optional[str]:
        return str(self._save_path) if self._save_path else None

    def load_existing(self, path: str) -> None:
        """Show a previously saved recording without re-recording."""
        p = Path(path)
        if p.exists():
            self._save_path = p
            duration = self._get_wav_duration(p)
            self._duration_label.setText(f"Duration: {duration:.1f}s")
            self._status.setText(f"Loaded: {p.name}")
            # Mark as having audio so Play/Clear work
            self._audio = np.zeros(1, dtype=np.float32)  # placeholder
            self._set_state("has_audio")

    @staticmethod
    def _get_wav_duration(path: Path) -> float:
        try:
            with wave.open(str(path), "rb") as wf:
                return wf.getnframes() / wf.getframerate()
        except Exception:
            return 0.0

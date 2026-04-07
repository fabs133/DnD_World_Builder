"""Small voice preview widget — generate + play + stop."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl


class _GenWorker(QThread):
    """Background generation thread."""
    finished = pyqtSignal(bytes)
    failed = pyqtSignal(str)

    def __init__(self, adapter, text, profile):
        super().__init__()
        self._adapter = adapter
        self._text = text
        self._profile = profile

    def run(self):
        try:
            audio = self._adapter.preview(self._text, self._profile)
            if audio:
                self.finished.emit(audio)
            else:
                self.failed.emit("Generation returned no audio")
        except Exception as e:
            self.failed.emit(str(e))


class VoicePreviewPlayer(QWidget):
    """[Preview] [Stop]  status label."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._adapter = None
        self._worker = None
        self._tmp_path: Path | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._play_btn = QPushButton("Preview")
        self._play_btn.setFixedWidth(80)
        self._play_btn.clicked.connect(self._on_preview)
        layout.addWidget(self._play_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setFixedWidth(50)
        self._stop_btn.clicked.connect(self._on_stop)
        layout.addWidget(self._stop_btn)

        self._status = QLabel("")
        self._status.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self._status, stretch=1)

    def set_adapter(self, adapter) -> None:
        self._adapter = adapter

    def preview(self, text: str, profile) -> None:
        """Start generating and playing a preview."""
        if not self._adapter:
            self._status.setText("Voice not available")
            return
        if not text.strip():
            self._status.setText("No text to preview")
            return

        self._status.setText("Generating...")
        self._play_btn.setEnabled(False)

        # Elapsed time counter
        import time
        self._gen_start = time.time()
        if not hasattr(self, "_elapsed_timer"):
            from PyQt5.QtCore import QTimer
            self._elapsed_timer = QTimer(self)
            self._elapsed_timer.setInterval(500)
            self._elapsed_timer.timeout.connect(self._update_elapsed)
        self._elapsed_timer.start()

        self._worker = _GenWorker(self._adapter, text, profile)
        self._worker.finished.connect(self._on_generated)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _update_elapsed(self) -> None:
        import time
        elapsed = time.time() - self._gen_start
        dots = "." * (int(elapsed * 2) % 4)
        self._status.setText(f"Generating{dots} ({elapsed:.0f}s)")

    def _on_preview(self) -> None:
        """Called by the Preview button — subclasses or parent should call preview()."""
        self._status.setText("Use preview() with text and profile")

    def _on_generated(self, audio_data: bytes) -> None:
        if hasattr(self, "_elapsed_timer"):
            self._elapsed_timer.stop()
        import time
        elapsed = time.time() - self._gen_start
        self._play_btn.setEnabled(True)
        self._status.setText(f"Playing... (generated in {elapsed:.1f}s)")

        self._tmp_path = Path(tempfile.mktemp(suffix=".wav"))
        self._tmp_path.write_bytes(audio_data)

        try:
            from core.audio_player import AudioPlayer
            from core.audio.audio_mixer import AudioChannel
            AudioPlayer.instance().play(str(self._tmp_path.resolve()), channel=AudioChannel.VOICE)
            self._status.setText("Done")
        except Exception as e:
            self._status.setText(f"Playback error: {e}")

    def _on_failed(self, msg: str) -> None:
        if hasattr(self, "_elapsed_timer"):
            self._elapsed_timer.stop()
        self._play_btn.setEnabled(True)
        self._status.setText(f"Failed: {msg}")

    def _on_stop(self) -> None:
        try:
            from core.audio_player import AudioPlayer
            AudioPlayer.instance().stop()
        except Exception:
            pass
        self._status.setText("Stopped")

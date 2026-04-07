"""DM Narration Panel — displays AlertGamemaster messages with voice readout."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout,
)
from PyQt5.QtCore import Qt


class NarrationPanel(QWidget):
    """Displays trigger narration messages in a styled parchment-like area.

    Subscribes to NARRATION_TRIGGERED events from the EventBus.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._messages: list[str] = []
        self._subscribed = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Title
        title = QLabel("Narration")
        title.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(title)

        # Narration display
        self._display = QTextEdit()
        self._display.setReadOnly(True)
        self._display.setStyleSheet(
            "QTextEdit { "
            "  background: #2a2520; "
            "  color: #d4c8a0; "
            "  border: 1px solid #554a3a; "
            "  border-radius: 4px; "
            "  padding: 8px; "
            "  font-size: 12px; "
            "  font-style: italic; "
            "}"
        )
        self._display.setPlaceholderText("Narration will appear here when triggers fire...")
        layout.addWidget(self._display, stretch=1)

        # Controls
        btn_row = QHBoxLayout()
        self._read_btn = QPushButton("Read Aloud")
        self._read_btn.setToolTip("Generate and play narration voice (narrator preset)")
        self._read_btn.clicked.connect(self._read_aloud)
        btn_row.addWidget(self._read_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear)
        btn_row.addWidget(clear_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Subscribe to narration events
        try:
            from core.gameCreation.event_bus import EventBus
            from core.events import NARRATION_TRIGGERED
            EventBus.subscribe(NARRATION_TRIGGERED, self._on_narration)
            self._subscribed = True
        except Exception:
            pass

    def _on_narration(self, data: dict) -> None:
        """Handle NARRATION_TRIGGERED event."""
        message = data.get("message", "")
        if not message:
            return
        self._messages.append(message)
        # Keep last 20 messages
        if len(self._messages) > 20:
            self._messages = self._messages[-20:]
        self._display.append(f'<p style="margin: 6px 0;">{message}</p>')
        # Auto-scroll to bottom
        sb = self._display.verticalScrollBar()
        sb.setValue(sb.maximum())

    def add_message(self, message: str) -> None:
        """Programmatically add a narration message."""
        self._on_narration({"message": message})

    def _read_aloud(self) -> None:
        """Generate and play the last narration message using narrator voice."""
        if not self._messages:
            return
        last_msg = self._messages[-1]
        try:
            from core.voice.voice_adapter import VoiceAdapter
            from core.voice.voice_profile import VoiceProfile
            adapter = VoiceAdapter.instance()
            if not adapter.is_available():
                return
            # Use narrator preset
            profile = adapter.create_profile("narrator")
            audio = adapter.preview(last_msg, profile)
            if audio:
                import tempfile
                from pathlib import Path
                tmp = Path(tempfile.mktemp(suffix=".wav"))
                tmp.write_bytes(audio)
                from core.audio_player import AudioPlayer
                from core.audio.audio_mixer import AudioChannel
                AudioPlayer.instance().play(str(tmp.resolve()), channel=AudioChannel.VOICE)
        except Exception:
            pass

    def _clear(self) -> None:
        self._messages.clear()
        self._display.clear()

    def cleanup(self) -> None:
        """Unsubscribe from events."""
        if self._subscribed:
            try:
                from core.gameCreation.event_bus import EventBus
                from core.events import NARRATION_TRIGGERED
                EventBus.unsubscribe(NARRATION_TRIGGERED, self._on_narration)
            except Exception:
                pass

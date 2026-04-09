"""Voice soundboard — clickable buttons for player voice lines."""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QGroupBox,
)
from PyQt5.QtCore import pyqtSignal, Qt

_OWN_BTN = (
    "QPushButton { background: rgba(40,80,50,200); color: #c0e8b0;"
    "  border: 1px solid rgba(100,180,100,80); border-radius: 4px;"
    "  padding: 4px 8px; font-size: 11px; }"
    "QPushButton:hover { background: rgba(60,110,70,220); color: #fff; }"
)
_OTHER_BTN = (
    "QPushButton { background: rgba(40,50,80,200); color: #b0c8e8;"
    "  border: 1px solid rgba(100,120,180,80); border-radius: 4px;"
    "  padding: 4px 8px; font-size: 11px; }"
    "QPushButton:hover { background: rgba(60,70,110,220); color: #fff; }"
)
_COLS = 3


class VoiceSoundboardWidget(QWidget):
    """Grid of voice line buttons grouped by player.

    Signals
    -------
    voice_line_triggered(str, str, str)
        Emitted when a player clicks their OWN line button.
        Args: (player_name, cache_key, text).
    """

    voice_line_triggered = pyqtSignal(str, str, str)

    def __init__(self, own_player_name: str = "",
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._own_name = own_player_name
        self._player_data: dict[str, list[dict]] = {}  # name → [{text, cache_key}]
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self.hide()

    def set_own_name(self, name: str) -> None:
        self._own_name = name

    def add_player_lines(self, player_name: str, lines: list[dict]) -> None:
        """Add or replace voice lines for a player.

        Each dict: ``{text, cache_key, category}``.
        """
        self._player_data[player_name] = lines
        self._rebuild()

    def remove_player_lines(self, player_name: str) -> None:
        self._player_data.pop(player_name, None)
        self._rebuild()

    def clear(self) -> None:
        self._player_data.clear()
        self._rebuild()

    def _rebuild(self) -> None:
        # Clear layout
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._player_data:
            self.hide()
            return

        # Own lines first, then others alphabetically
        order = []
        if self._own_name in self._player_data:
            order.append(self._own_name)
        for name in sorted(self._player_data):
            if name != self._own_name:
                order.append(name)

        for name in order:
            lines = self._player_data[name]
            is_own = (name == self._own_name)
            title = "Your Lines" if is_own else f"{name}'s Lines"

            group = QGroupBox(title)
            group.setStyleSheet(
                "QGroupBox { color: #e8c840; font-size: 11px; font-weight: bold;"
                "  border: 1px solid rgba(200,170,100,40); border-radius: 4px;"
                "  margin-top: 6px; padding-top: 12px; }"
                "QGroupBox::title { padding: 0 4px; }")
            grid = QGridLayout(group)
            grid.setSpacing(4)
            grid.setContentsMargins(4, 4, 4, 4)

            for i, line_data in enumerate(lines):
                text = line_data.get("text", "???")
                cache_key = line_data.get("cache_key", "")
                label = text[:18] + "..." if len(text) > 18 else text

                btn = QPushButton(label)
                btn.setToolTip(text)
                btn.setStyleSheet(_OWN_BTN if is_own else _OTHER_BTN)
                btn.setCursor(Qt.PointingHandCursor)

                if is_own:
                    btn.clicked.connect(
                        lambda _, n=name, k=cache_key, t=text:
                            self._on_own_clicked(n, k, t))
                else:
                    btn.clicked.connect(
                        lambda _, k=cache_key: self._play_from_cache(k))

                grid.addWidget(btn, i // _COLS, i % _COLS)

            self._layout.addWidget(group)

        self._layout.addStretch()
        self.show()

    def _on_own_clicked(self, player_name: str, cache_key: str,
                        text: str) -> None:
        """Play locally AND signal for network broadcast."""
        self._play_from_cache(cache_key)
        self.voice_line_triggered.emit(player_name, cache_key, text)

    def _play_from_cache(self, cache_key: str) -> None:
        """Look up audio in cache and play it."""
        try:
            from core.voice.voice_cache import VoiceCache
            cache = VoiceCache(Path("assets/voice_cache"))
            path = cache.get(cache_key)
            if path and path.exists():
                from core.audio_player import AudioPlayer, AudioChannel
                AudioPlayer.instance().play(str(path), AudioChannel.VOICE)
        except Exception:
            pass

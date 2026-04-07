"""Scenario introduction screen with cinematic typewriter reveal."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit,
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

from ui.widgets.ornamental_divider import OrnamentalDivider


class ScenarioIntroWidget(QWidget):
    """Cinematic scenario intro with typewriter text reveal.

    Shows scenario title with a fade-in feel, then reveals the
    description text character by character. The "Begin Adventure"
    button appears after the text finishes (or on any click to skip).

    Emits :pyqtSignal:`begin_requested` when the user is ready to play.
    """

    begin_requested = pyqtSignal()

    def __init__(self, scenario_name: str, description: str = "",
                 parent=None):
        super().__init__(parent)
        self._full_text = description or "Your adventure begins..."
        self._char_index = 0

        self.setStyleSheet("background: rgb(24, 22, 20);")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 60, 60, 60)

        layout.addStretch(2)

        # Title
        self._title = QLabel(scenario_name)
        self._title.setProperty("themeRole", "panel-header")
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setStyleSheet(
            "font-size: 28px; font-weight: bold; color: #d4c9a8;"
            "font-family: Cinzel, serif; letter-spacing: 2px;")
        layout.addWidget(self._title)

        layout.addWidget(OrnamentalDivider())
        layout.addSpacing(16)

        # Description — typewriter reveal
        self._desc = QTextEdit()
        self._desc.setReadOnly(True)
        self._desc.setMaximumHeight(220)
        self._desc.setStyleSheet(
            "QTextEdit { background: transparent; color: #c8c0b0;"
            "  font-size: 14px; font-style: italic; border: none;"
            "  font-family: 'Georgia', serif; line-height: 1.6; }")
        self._desc.setPlainText("")
        layout.addWidget(self._desc)

        layout.addStretch(2)

        # Begin button — hidden until typewriter finishes
        self._btn = QPushButton("Begin Adventure")
        self._btn.setProperty("themeRole", "primary")
        self._btn.setFont(QFont("Cinzel", 14))
        self._btn.setStyleSheet(
            "QPushButton { padding: 10px 30px; }")
        self._btn.clicked.connect(self.begin_requested.emit)
        self._btn.hide()
        layout.addWidget(self._btn, alignment=Qt.AlignCenter)

        layout.addStretch(1)

        # Typewriter timer
        self._type_timer = QTimer(self)
        self._type_timer.timeout.connect(self._type_next_char)

    def showEvent(self, event):
        super().showEvent(event)
        # Start typewriter after a short delay
        self._char_index = 0
        self._desc.setPlainText("")
        self._btn.hide()
        QTimer.singleShot(600, self._start_typewriter)

    def _start_typewriter(self):
        if self._full_text:
            self._type_timer.start(30)  # ~33 chars/sec

    def _type_next_char(self):
        if self._char_index >= len(self._full_text):
            self._type_timer.stop()
            self._btn.show()
            return
        self._char_index += 1
        self._desc.setPlainText(self._full_text[:self._char_index])
        # Auto-scroll
        sb = self._desc.verticalScrollBar()
        sb.setValue(sb.maximum())

    def mousePressEvent(self, event):
        """Click anywhere to skip the typewriter and show full text."""
        if self._type_timer.isActive():
            self._type_timer.stop()
            self._desc.setPlainText(self._full_text)
            self._btn.show()
        else:
            super().mousePressEvent(event)

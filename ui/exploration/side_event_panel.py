"""Interaction panel for side events on empty tiles."""

from __future__ import annotations

import random

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer

_PANEL_STYLE = (
    "background: rgba(20, 18, 16, 230);"
    "color: #e0d8c8; border: 1px solid rgba(200, 170, 100, 80);"
    "border-radius: 10px;"
)
_TITLE_STYLE = "color: #e8c840; font-size: 15px; font-weight: bold;"
_NARRATIVE_STYLE = "color: #d0c8b8; font-size: 13px; line-height: 1.4;"
_BTN_STYLE = (
    "QPushButton { background: rgba(60,55,45,200); color: #e0d8c8;"
    "border: 1px solid rgba(200,170,100,60); border-radius: 5px;"
    "padding: 6px 14px; font-size: 12px; }"
    "QPushButton:hover { background: rgba(100,90,60,200); color: #fff; }"
)
_BTN_DISMISS_STYLE = (
    "QPushButton { background: rgba(40,38,34,200); color: #a09880;"
    "border: 1px solid rgba(120,100,60,40); border-radius: 5px;"
    "padding: 6px 14px; font-size: 12px; }"
    "QPushButton:hover { background: rgba(70,65,55,200); color: #c0b8a0; }"
)
_RESULT_PASS = "color: #8dce6a; font-size: 13px; font-weight: bold;"
_RESULT_FAIL = "color: #e07050; font-size: 13px; font-weight: bold;"
_RESULT_INFO = "color: #d0c8b8; font-size: 13px;"


# ── Dice roll animation ────────────────────────────────────────

_DICE_NUM_STYLE = (
    "color: #e8c840; font-size: 48px; font-weight: bold;"
    "font-family: 'Consolas', 'Courier New', monospace;"
    "min-height: 60px; min-width: 70px;"
)
_DICE_BREAKDOWN_STYLE = "color: #c0b8a0; font-size: 13px;"
_DICE_PASS_STYLE = "color: #8dce6a; font-size: 18px; font-weight: bold;"
_DICE_FAIL_STYLE = "color: #e07050; font-size: 18px; font-weight: bold;"

# Tick intervals: 18 fast + 3 medium + 2 slow + 1 final
_ROLL_INTERVALS = [50] * 18 + [80] * 3 + [120] * 2 + [180]


class DiceRollWidget(QWidget):
    """Animated d20 roll that cycles numbers, lands on the real result."""

    roll_complete = pyqtSignal(bool)  # emits passed

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(4)

        self._dice_label = QLabel("d20")
        self._dice_label.setStyleSheet(_DICE_NUM_STYLE)
        self._dice_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._dice_label, alignment=Qt.AlignCenter)

        self._breakdown = QLabel()
        self._breakdown.setStyleSheet(_DICE_BREAKDOWN_STYLE)
        self._breakdown.setAlignment(Qt.AlignCenter)
        self._breakdown.hide()
        layout.addWidget(self._breakdown, alignment=Qt.AlignCenter)

        self._verdict = QLabel()
        self._verdict.setAlignment(Qt.AlignCenter)
        self._verdict.hide()
        layout.addWidget(self._verdict, alignment=Qt.AlignCenter)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._tick_idx = 0
        self._actual_roll = 1
        self._mod = 0
        self._mod_label = ""
        self._dc = 10
        self._passed = False
        self._on_complete = None
        self.hide()

    def start_roll(self, actual_roll: int, modifier: int, mod_label: str,
                   dc: int, passed: bool, on_complete=None) -> None:
        self._actual_roll = actual_roll
        self._mod = modifier
        self._mod_label = mod_label
        self._dc = dc
        self._passed = passed
        self._on_complete = on_complete
        self._tick_idx = 0
        self._breakdown.hide()
        self._verdict.hide()
        self._dice_label.setText("d20")
        self._dice_label.setStyleSheet(_DICE_NUM_STYLE)
        self.show()
        self._timer.start(_ROLL_INTERVALS[0])

    def _tick(self) -> None:
        self._tick_idx += 1
        if self._tick_idx < len(_ROLL_INTERVALS):
            # Cycling phase — show random number
            self._dice_label.setText(str(random.randint(1, 20)))
            self._timer.setInterval(_ROLL_INTERVALS[self._tick_idx])
        elif self._tick_idx == len(_ROLL_INTERVALS):
            # Landing — show actual roll
            self._timer.stop()
            self._dice_label.setText(str(self._actual_roll))

            # Play dice sound
            try:
                from core.audio.ui_sound_manager import UISoundManager, SoundCategory
                UISoundManager.instance().play("dice", SoundCategory.COMBAT)
            except Exception:
                pass

            # Show breakdown after short pause
            QTimer.singleShot(300, self._show_breakdown)

    def _show_breakdown(self) -> None:
        total = self._actual_roll + self._mod
        self._breakdown.setText(
            f"d20({self._actual_roll}) + {self._mod_label}({self._mod:+d}) = {total}"
            f"  vs DC {self._dc}"
        )
        self._breakdown.show()
        QTimer.singleShot(400, self._show_verdict)

    def _show_verdict(self) -> None:
        if self._passed:
            self._verdict.setStyleSheet(_DICE_PASS_STYLE)
            self._verdict.setText("Success!")
            self._dice_label.setStyleSheet(
                _DICE_NUM_STYLE + "color: #8dce6a;")
        else:
            self._verdict.setStyleSheet(_DICE_FAIL_STYLE)
            self._verdict.setText("Failed.")
            self._dice_label.setStyleSheet(
                _DICE_NUM_STYLE + "color: #e07050;")
        self._verdict.show()
        QTimer.singleShot(600, self._emit_complete)

    def _emit_complete(self) -> None:
        self.roll_complete.emit(self._passed)
        if self._on_complete:
            self._on_complete(self._passed)


class SideEventPanel(QWidget):
    """Overlay panel for interacting with a side event.

    Signals
    -------
    action_clicked(str)
        Emitted when the player clicks an action button.
        Values: "examine", "move_on", "check", "skip",
                "search", "choice_0", "choice_1", "choice_2", "continue".
    """

    action_clicked = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(_PANEL_STYLE)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(8)

        self._title = QLabel()
        self._title.setStyleSheet(_TITLE_STYLE)
        self._title.setWordWrap(True)
        root.addWidget(self._title)

        self._narrative = QLabel()
        self._narrative.setStyleSheet(_NARRATIVE_STYLE)
        self._narrative.setWordWrap(True)
        root.addWidget(self._narrative)

        self._result_label = QLabel()
        self._result_label.setWordWrap(True)
        self._result_label.hide()
        root.addWidget(self._result_label)

        self._dice_widget = DiceRollWidget(self)
        self._dice_widget.hide()
        root.addWidget(self._dice_widget)

        self._btn_row = QHBoxLayout()
        self._btn_row.setSpacing(8)
        root.addLayout(self._btn_row)

        self.hide()

    # ── Public API ─────────────────────────────────────────────────

    def show_event(self, title: str, narrative: str,
                   buttons: list[dict]) -> None:
        """Display the event with action buttons.

        Parameters
        ----------
        title : str
            Event variant name.
        narrative : str
            Descriptive text.
        buttons : list[dict]
            Each dict: {"label": str, "action": str, "style": "action"|"dismiss"}
        """
        self._title.setText(title)
        self._narrative.setText(narrative)
        self._narrative.show()
        self._result_label.hide()
        self._dice_widget.hide()
        self._set_buttons(buttons)
        self.show()
        self.raise_()

    def show_result(self, text: str, passed: bool | None = None) -> None:
        """Replace narrative with a result, show Continue button."""
        self._narrative.hide()
        self._dice_widget.hide()
        if passed is True:
            self._result_label.setStyleSheet(_RESULT_PASS)
        elif passed is False:
            self._result_label.setStyleSheet(_RESULT_FAIL)
        else:
            self._result_label.setStyleSheet(_RESULT_INFO)
        self._result_label.setText(text)
        self._result_label.show()
        self._set_buttons([
            {"label": "Continue", "action": "continue", "style": "dismiss"},
        ])

    def show_dice_roll(self, actual_roll: int, modifier: int, mod_label: str,
                       dc: int, passed: bool, on_complete=None) -> None:
        """Transition the panel to show an animated dice roll."""
        self._narrative.hide()
        self._result_label.hide()
        # Clear buttons during animation
        while self._btn_row.count():
            item = self._btn_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._dice_widget.start_roll(actual_roll, modifier, mod_label, dc,
                                     passed, on_complete=on_complete)

    def show_completed(self, title: str, short_text: str) -> None:
        """Show abbreviated view for already-completed events."""
        self._title.setText(title)
        self._narrative.setText(short_text)
        self._narrative.show()
        self._result_label.hide()
        self._set_buttons([
            {"label": "Continue", "action": "continue", "style": "dismiss"},
        ])
        self.show()
        self.raise_()

    # ── Internals ──────────────────────────────────────────────────

    def _set_buttons(self, buttons: list[dict]) -> None:
        while self._btn_row.count():
            item = self._btn_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._btn_row.addStretch()
        for bdef in buttons:
            btn = QPushButton(bdef["label"])
            style = _BTN_DISMISS_STYLE if bdef.get("style") == "dismiss" else _BTN_STYLE
            btn.setStyleSheet(style)
            btn.setCursor(Qt.PointingHandCursor)
            action = bdef["action"]
            btn.clicked.connect(lambda checked, a=action: self.action_clicked.emit(a))
            self._btn_row.addWidget(btn)
        self._btn_row.addStretch()

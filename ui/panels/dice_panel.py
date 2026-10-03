"""
Dice Roller Panel
=================

Dockable panel for rolling dice expressions (``2d6+3``, ``2d20kh1`` ...).
Offline it rolls locally with :mod:`core.engine.dice`; inside a multiplayer
session :meth:`DicePanel.set_remote` redirects rolls to the host as
``/roll <expr>`` chat lines so everyone sees the same authoritative result.
"""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.engine import dice

HISTORY_LIMIT = 50

QUICK_BUTTONS = (
    ("d4", "d4"),
    ("d6", "d6"),
    ("d8", "d8"),
    ("d10", "d10"),
    ("d12", "d12"),
    ("d20", "d20"),
    ("d100", "d100"),
    ("Adv", "2d20kh1"),
    ("Dis", "2d20kl1"),
)


class DicePanel(QWidget):
    """Expression input, quick buttons and a roll history.

    Signals:
        roll_requested(str): Emitted with the (valid) expression on every roll.
    """

    roll_requested = pyqtSignal(str)

    def __init__(self, parent=None, rng=None):
        super().__init__(parent)
        self._rng = rng
        self._remote = None
        self.quick_buttons = {}

        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        self.expression_edit = QLineEdit()
        self.expression_edit.setPlaceholderText("e.g. 2d6+3, d20, 2d20kh1")
        self.expression_edit.returnPressed.connect(self.roll_current)
        row.addWidget(self.expression_edit)
        self.roll_button = QPushButton("Roll")
        self.roll_button.clicked.connect(self.roll_current)
        row.addWidget(self.roll_button)
        layout.addLayout(row)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #d32f2f;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        quick = QHBoxLayout()
        for label, expr in QUICK_BUTTONS:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _checked=False, e=expr: self.roll(e))
            quick.addWidget(btn)
            self.quick_buttons[label] = btn
        layout.addLayout(quick)

        self.history = QListWidget()
        layout.addWidget(self.history)

    # ------------------------------------------------------------------

    def set_remote(self, sender):
        """Route rolls through *sender* (``callable(str)``) or roll locally.

        :param sender: Callable taking the chat text (``"/roll <expr>"``), or
            ``None`` when not in a session.
        """
        self._remote = sender

    def roll_current(self):
        """Roll whatever is in the expression box."""
        self.roll(self.expression_edit.text())

    def roll(self, expression):
        """Validate and roll *expression* (locally, or via the remote sender).

        :return: ``True`` if the expression was valid.
        """
        expression = expression.strip()
        try:
            dice.parse(expression)
        except ValueError as exc:
            self._show_error(str(exc))
            return False
        self._show_error("")
        self.expression_edit.setText(expression)
        self.roll_requested.emit(expression)
        if self._remote is not None:
            self._remote("/roll " + expression)
        else:
            result = dice.roll(expression, rng=self._rng)
            self.add_history(dice.format_roll(result))
        return True

    def add_history(self, text):
        """Insert *text* at the top of the history, capped at 50 entries."""
        self.history.insertItem(0, text)
        while self.history.count() > HISTORY_LIMIT:
            self.history.takeItem(self.history.count() - 1)

    def _show_error(self, text):
        self.error_label.setText(text)
        self.error_label.setVisible(bool(text))

"""Exploration action bar — context-sensitive actions for non-combat play."""

from __future__ import annotations

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QFrame
from PyQt5.QtCore import pyqtSignal


class ExplorationBarPanel(QWidget):
    """Action bar shown during exploration mode.

    Signals
    -------
    action_selected(str)
        Emitted with ``"interact"``, ``"search"``, or ``"sneak"``.
    rest_requested(str)
        Emitted with ``"short_rest"`` or ``"long_rest"``.
    """

    action_selected = pyqtSignal(str)
    rest_requested = pyqtSignal(str)

    _ACTION_BUTTONS = [
        ("interact", "Interact", "Talk to an NPC or examine an object"),
        ("search", "Search", "Perception check — find hidden features"),
        ("sneak", "Sneak", "Stealth check before entering a zone"),
        ("inventory", "Inventory", "View party inventory and equipment"),
    ]

    _REST_BUTTONS = [
        ("short_rest", "Short Rest", "1 hour — spend Hit Dice to recover HP"),
        ("long_rest", "Long Rest", "8 hours — restore all HP and spell slots"),
    ]

    def __init__(self, role: str = "player", parent: QWidget | None = None):
        super().__init__(parent)
        self._buttons: dict[str, QPushButton] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        for action_id, label, tooltip in self._ACTION_BUTTONS:
            btn = QPushButton(label)
            btn.setToolTip(tooltip)
            btn.setMinimumHeight(32)
            btn.clicked.connect(lambda checked, a=action_id: self.action_selected.emit(a))
            layout.addWidget(btn)
            self._buttons[action_id] = btn

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        for rest_id, label, tooltip in self._REST_BUTTONS:
            btn = QPushButton(label)
            btn.setToolTip(tooltip)
            btn.setMinimumHeight(32)
            btn.clicked.connect(lambda checked, r=rest_id: self.rest_requested.emit(r))
            layout.addWidget(btn)
            self._buttons[rest_id] = btn

        layout.addStretch()

        if role == "spectator":
            self.set_enabled(False)

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------

    def set_enabled(self, enabled: bool) -> None:
        """Master enable / disable all buttons."""
        for btn in self._buttons.values():
            btn.setEnabled(enabled)

    def set_interact_enabled(self, enabled: bool) -> None:
        if "interact" in self._buttons:
            self._buttons["interact"].setEnabled(enabled)

    def set_rest_available(self, short: bool = True, long: bool = True) -> None:
        if "short_rest" in self._buttons:
            self._buttons["short_rest"].setEnabled(short)
        if "long_rest" in self._buttons:
            self._buttons["long_rest"].setEnabled(long)

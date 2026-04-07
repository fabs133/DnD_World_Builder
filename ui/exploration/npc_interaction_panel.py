"""Contextual interaction panel for NPC/object clicks."""

from __future__ import annotations

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import pyqtSignal


class NpcInteractionPanel(QWidget):
    """Floating panel with interaction buttons for a selected entity.

    Signals:
        interaction_chosen(str, str): (entity_name, interaction_id)
        dismissed(): Panel closed.
    """

    interaction_chosen = pyqtSignal(str, str)
    dismissed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entity_name = ""
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 4, 8, 4)
        self.hide()

    def show_for_entity(self, entity_name: str, interactions: list[dict]) -> None:
        """Populate and show the panel."""
        self._entity_name = entity_name

        # Clear existing buttons
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedWidth(24)
        close_btn.clicked.connect(self.hide_panel)
        self._layout.addWidget(close_btn)

        # Entity name
        self._layout.addWidget(QLabel(f"<b>{entity_name}</b>"))

        # Interaction buttons
        for inter in interactions:
            btn = QPushButton(inter["label"])
            btn.setEnabled(inter.get("enabled", True))
            if not inter.get("enabled", True):
                btn.setToolTip(inter.get("reason", ""))
            btn.clicked.connect(
                lambda checked, iid=inter["id"]: self.interaction_chosen.emit(
                    self._entity_name, iid
                )
            )
            self._layout.addWidget(btn)

        self.show()

    def hide_panel(self) -> None:
        self.hide()
        self.dismissed.emit()

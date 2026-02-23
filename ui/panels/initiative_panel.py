"""
Initiative Tracker Panel
========================

Dockable panel displaying D&D initiative order during a game session.
Shows entity names, initiative rolls, HP bars, and highlights the
current turn.  Designed to be embedded in a ``QDockWidget`` inside
:class:`~ui.main_window.MainWindow`.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton,
    QProgressBar,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor


class InitiativePanel(QWidget):
    """Panel that displays the current initiative order and round info.

    Call :meth:`set_initiative_order` to populate the list and
    :meth:`set_current_turn` to highlight the active entity.

    Signals:
        entity_selected(str): Emitted when the user clicks an entity row.
    """

    entity_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[dict] = []
        self._current_entity: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Header
        self._header = QLabel("Initiative Tracker")
        self._header.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self._header)

        # Round indicator
        self._round_label = QLabel("Round: --")
        self._round_label.setStyleSheet("color: gray;")
        layout.addWidget(self._round_label)

        # Initiative list
        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self._list)

        # Action buttons
        btn_row = QHBoxLayout()
        self._next_btn = QPushButton("Next Turn")
        self._next_btn.setEnabled(False)
        btn_row.addWidget(self._next_btn)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_initiative_order(self, entries: list[dict]) -> None:
        """Populate the initiative list.

        Each entry dict should have:
            - ``name``: entity name
            - ``roll``: initiative roll total
            - ``hp``: current HP (optional)
            - ``max_hp``: max HP (optional)
            - ``entity_type``: "player"/"enemy"/"npc" (optional)

        :param entries: Initiative entries in order (highest first).
        """
        self._entries = list(entries)
        self._rebuild_list()

    def set_current_turn(self, entity_name: str, round_number: int) -> None:
        """Highlight the entity whose turn it is.

        :param entity_name: Name of the current entity.
        :param round_number: Current round number.
        """
        self._current_entity = entity_name
        self._round_label.setText(f"Round: {round_number}")
        self._highlight_current()

    def update_entity_hp(self, entity_name: str, hp: int, max_hp: int) -> None:
        """Update HP display for a single entity without rebuilding.

        :param entity_name: Name of the entity.
        :param hp: Current HP.
        :param max_hp: Maximum HP.
        """
        for entry in self._entries:
            if entry["name"] == entity_name:
                entry["hp"] = hp
                entry["max_hp"] = max_hp
                break
        self._rebuild_list()

    def clear(self) -> None:
        """Reset the panel to its empty state."""
        self._entries = []
        self._current_entity = None
        self._list.clear()
        self._round_label.setText("Round: --")

    @property
    def next_turn_button(self) -> QPushButton:
        """Access the Next Turn button for external wiring."""
        return self._next_btn

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _rebuild_list(self) -> None:
        self._list.clear()
        for entry in self._entries:
            item = QListWidgetItem()
            widget = _InitiativeRow(entry)
            item.setSizeHint(widget.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)
        self._highlight_current()

    def _highlight_current(self) -> None:
        for i in range(self._list.count()):
            item = self._list.item(i)
            widget = self._list.itemWidget(item)
            if widget and widget.entity_name == self._current_entity:
                item.setBackground(QColor("#2d2d5e"))
                widget.set_active(True)
            else:
                item.setBackground(QColor("transparent"))
                if widget:
                    widget.set_active(False)

    def _on_row_changed(self, row: int) -> None:
        if 0 <= row < len(self._entries):
            self.entity_selected.emit(self._entries[row]["name"])


class _InitiativeRow(QWidget):
    """Single row in the initiative list."""

    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.entity_name = entry["name"]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        # Initiative roll badge
        roll_label = QLabel(str(entry.get("roll", "?")))
        roll_label.setFixedWidth(28)
        roll_label.setAlignment(Qt.AlignCenter)
        roll_label.setStyleSheet(
            "font-weight: bold; background: #444; color: white; "
            "border-radius: 4px; padding: 2px;"
        )
        layout.addWidget(roll_label)

        # Entity name + type
        name_text = entry["name"]
        entity_type = entry.get("entity_type", "")
        if entity_type:
            name_text += f"  ({entity_type})"
        self._name_label = QLabel(name_text)
        layout.addWidget(self._name_label, stretch=1)

        # HP bar (if available)
        hp = entry.get("hp")
        max_hp = entry.get("max_hp")
        if hp is not None and max_hp is not None and max_hp > 0:
            hp_bar = QProgressBar()
            hp_bar.setRange(0, max_hp)
            hp_bar.setValue(max(0, hp))
            hp_bar.setFormat(f"{hp}/{max_hp}")
            hp_bar.setFixedWidth(80)
            hp_bar.setFixedHeight(16)
            layout.addWidget(hp_bar)

    def set_active(self, active: bool) -> None:
        """Toggle the active (current turn) highlight."""
        if active:
            self._name_label.setStyleSheet("font-weight: bold; color: #c084fc;")
        else:
            self._name_label.setStyleSheet("")

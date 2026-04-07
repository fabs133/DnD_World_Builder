"""Card-style trigger list panel for the tile side panel."""

from __future__ import annotations

from typing import Any, List

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea,
)
from PyQt5.QtCore import Qt, pyqtSignal


# Event type colors
_EVENT_COLORS = {
    "ENTER_TILE": "#3b82f6",      # blue
    "LEAVE_TILE": "#3b82f6",
    "ON_DAMAGE": "#f59e0b",       # amber
    "ON_TURN_START": "#f59e0b",
    "TURN_START": "#f59e0b",
    "PLAYER_IN_RANGE": "#14b8a6", # teal
    "CUSTOM": "#8b5cf6",          # purple
}


def _format_condition(condition: Any) -> str:
    """Human-readable condition description."""
    cls_name = condition.__class__.__name__
    if cls_name == "AlwaysTrue":
        return "Always fires"
    if cls_name == "AlwaysFalse":
        return "Never fires"
    # Try to extract meaningful info
    attrs = []
    for attr in ("dc", "skill", "ability", "threshold", "condition"):
        val = getattr(condition, attr, None)
        if val is not None:
            attrs.append(f"{attr}={val}")
    if attrs:
        return f"{cls_name}({', '.join(attrs)})"
    return cls_name


def _format_reaction(reaction: Any) -> str:
    """Human-readable reaction description."""
    cls_name = reaction.__class__.__name__
    if cls_name == "ApplyDamage":
        dtype = getattr(reaction, "damage_type", "")
        amount = getattr(reaction, "amount", "?")
        return f"Deal {amount} {dtype} damage"
    if cls_name == "AlertGamemaster":
        msg = getattr(reaction, "message", "")
        return f'Alert GM: "{msg[:30]}"'
    if cls_name == "PlaySound":
        sf = getattr(reaction, "sound_file", "")
        return f"Play sound: {sf}"
    return cls_name


class TriggerCard(QFrame):
    """A card showing one trigger's details.

    Signals:
        edit_requested(str): Trigger label to edit.
        delete_requested(str): Trigger label to delete.
    """

    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, trigger: Any, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self._trigger = trigger

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(3)

        # Header: event type with color
        event_type = getattr(trigger, "event_type", "CUSTOM")
        label = getattr(trigger, "label", "")
        color = _EVENT_COLORS.get(event_type, "#6b7280")

        header = QLabel(f"<b style='color:{color}'>{event_type}</b>")
        layout.addWidget(header)

        # Condition
        condition = getattr(trigger, "condition", None)
        if condition:
            cond_text = _format_condition(condition)
            layout.addWidget(QLabel(f"If: {cond_text}"))

        # Reaction
        reaction = getattr(trigger, "reaction", None)
        if reaction:
            react_text = _format_reaction(reaction)
            layout.addWidget(QLabel(f"Then: {react_text}"))

        # Chain
        next_trigger = getattr(trigger, "next_trigger", None)
        if next_trigger:
            layout.addWidget(QLabel(f"→ {next_trigger}"))

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        edit_btn = QPushButton("Edit")
        edit_btn.setFixedWidth(50)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(label))
        btn_row.addWidget(edit_btn)
        del_btn = QPushButton("×")
        del_btn.setFixedWidth(24)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(label))
        btn_row.addWidget(del_btn)
        layout.addLayout(btn_row)


class TriggerListPanel(QWidget):
    """Scrollable card list of all triggers on a tile.

    Signals:
        trigger_added(): User wants to add a trigger.
        trigger_edited(str): Trigger label to edit.
        trigger_deleted(str): Trigger label to delete.
        graph_view_requested(): Open advanced graph editor.
    """

    trigger_added = pyqtSignal()
    trigger_edited = pyqtSignal(str)
    trigger_deleted = pyqtSignal(str)
    graph_view_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tile_data = None
        self._cards: list[TriggerCard] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Add button
        add_btn = QPushButton("+ Add Trigger")
        add_btn.clicked.connect(self.trigger_added.emit)
        layout.addWidget(add_btn)

        # Scroll area for cards
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._container = QWidget()
        self._card_layout = QVBoxLayout(self._container)
        self._card_layout.setAlignment(Qt.AlignTop)
        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)

        # Empty state message
        self._empty_label = QLabel(
            "No triggers on this tile.\n\n"
            "Triggers let you create traps, scripted events, "
            "and NPC reactions.\nClick + Add to create one."
        )
        self._empty_label.setWordWrap(True)
        self._empty_label.setStyleSheet("color: gray; font-style: italic; padding: 12px;")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._card_layout.addWidget(self._empty_label)

        # Graph view button
        graph_btn = QPushButton("Advanced: Graph View...")
        graph_btn.clicked.connect(self.graph_view_requested.emit)
        layout.addWidget(graph_btn)

    def set_tile(self, tile_data: Any) -> None:
        """Populate from tile's triggers."""
        self._tile_data = tile_data
        self._refresh()

    def _refresh(self) -> None:
        # Clear existing cards
        for card in self._cards:
            self._card_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        triggers = getattr(self._tile_data, "triggers", []) if self._tile_data else []
        self._empty_label.setVisible(len(triggers) == 0)

        for trigger in triggers:
            card = TriggerCard(trigger)
            card.edit_requested.connect(self.trigger_edited.emit)
            card.delete_requested.connect(self.trigger_deleted.emit)
            self._card_layout.insertWidget(self._card_layout.count() - 1, card)  # before graph btn
            self._cards.append(card)

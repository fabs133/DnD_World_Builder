"""Player combat action bar.

Displays movement counter, action buttons, bonus/reaction indicators,
spell slot pills, and End Turn button. Reads from CombatHUDProvider.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal


class ActionBarPanel(QWidget):
    """Player-facing combat action bar.

    Signals:
        action_selected(str): Action ID (attack, dash, dodge, disengage, help).
        spell_cast_requested(): Opens the spell selector dialog.
        end_turn_requested(): Player ends their turn.
    """

    action_selected = pyqtSignal(str)
    spell_cast_requested = pyqtSignal()
    end_turn_requested = pyqtSignal()

    _ACTION_BUTTONS = [
        ("attack", "Attack (1)", "Make a melee or ranged attack"),
        ("cast_spell", "Spell (2)", "Cast a spell (opens spell selector)"),
        ("dash", "Dash (3)", "Double your movement this turn"),
        ("dodge", "Dodge (4)", "Attacks against you have disadvantage"),
        ("disengage", "Disengage (5)", "Move without provoking opportunity attacks"),
        ("help", "Help (6)", "Give an ally advantage on their next check"),
    ]

    def __init__(self, role: str = "player", parent=None):
        super().__init__(parent)
        self._role = role
        self._action_btns: dict[str, QPushButton] = {}
        self._is_your_turn = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Movement section
        move_frame = QFrame()
        move_layout = QVBoxLayout(move_frame)
        move_layout.setContentsMargins(4, 2, 4, 2)
        self._move_label = QLabel("Move: --/-- ft")
        self._move_label.setAlignment(Qt.AlignCenter)
        move_layout.addWidget(self._move_label)
        layout.addWidget(move_frame)

        # Action buttons
        for action_id, label, tooltip in self._ACTION_BUTTONS:
            btn = QPushButton(label)
            btn.setToolTip(tooltip)
            btn.setEnabled(False)
            if action_id == "cast_spell":
                btn.clicked.connect(self.spell_cast_requested.emit)
            else:
                btn.clicked.connect(lambda checked, aid=action_id: self.action_selected.emit(aid))
            self._action_btns[action_id] = btn
            layout.addWidget(btn)

        # Bonus / Reaction indicators
        indicator_layout = QVBoxLayout()
        indicator_layout.setSpacing(2)
        self._bonus_label = QLabel("Bonus: --")
        self._bonus_label.setStyleSheet("font-size: 11px;")
        indicator_layout.addWidget(self._bonus_label)
        self._reaction_label = QLabel("Reaction: --")
        self._reaction_label.setStyleSheet("font-size: 11px;")
        indicator_layout.addWidget(self._reaction_label)
        layout.addLayout(indicator_layout)

        # Spell slot pills
        self._slot_frame = QFrame()
        self._slot_layout = QHBoxLayout(self._slot_frame)
        self._slot_layout.setContentsMargins(0, 0, 0, 0)
        self._slot_layout.setSpacing(4)
        layout.addWidget(self._slot_frame)

        layout.addStretch()

        # Waiting label (shown when not your turn)
        self._waiting_label = QLabel("")
        self._waiting_label.setStyleSheet("color: gray; font-style: italic;")
        self._waiting_label.hide()
        layout.addWidget(self._waiting_label)

        # End turn button
        self._end_turn_btn = QPushButton("End Turn")
        self._end_turn_btn.setToolTip("End your turn (Space)")
        self._end_turn_btn.setEnabled(False)
        self._end_turn_btn.clicked.connect(self.end_turn_requested.emit)
        layout.addWidget(self._end_turn_btn)

    def update_from_hud(self, data: dict) -> None:
        """Update all widgets from CombatHUDProvider.get_action_bar() data."""
        move_rem = data.get("movement_remaining", 0)
        move_max = data.get("movement_max", 30)
        self._move_label.setText(f"Move: {move_rem}/{move_max} ft")

        # Action buttons
        actions = data.get("actions", [])
        action_ids = {a["id"] for a in actions if a.get("enabled", True)}
        for aid, btn in self._action_btns.items():
            btn.setEnabled(aid in action_ids and self._is_your_turn)

        # Bonus / Reaction
        bonus_actions = data.get("bonus_actions", [])
        has_bonus = any(a.get("enabled", True) for a in bonus_actions)
        self._bonus_label.setText(f"Bonus: {'Available' if has_bonus else 'Used'}")

        reaction = data.get("reaction_available", False)
        self._reaction_label.setText(f"Reaction: {'Available' if reaction else 'Used'}")

        # Spell slots
        self._rebuild_spell_slots(data.get("spell_slots", {}))

    def set_your_turn(self, is_your_turn: bool, current_name: str = "") -> None:
        """Enable/disable all controls based on turn ownership."""
        self._is_your_turn = is_your_turn
        self._end_turn_btn.setEnabled(is_your_turn)

        for btn in self._action_btns.values():
            btn.setEnabled(is_your_turn)

        if is_your_turn:
            self._waiting_label.hide()
        else:
            self._waiting_label.setText(f"Waiting for {current_name}'s turn...")
            self._waiting_label.show()

    def _rebuild_spell_slots(self, slots: dict) -> None:
        """Rebuild spell slot pill labels."""
        # Clear existing
        while self._slot_layout.count():
            item = self._slot_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not slots:
            return

        for level, info in sorted(slots.items()):
            if isinstance(info, dict):
                used = info.get("used", 0)
                maximum = info.get("maximum", 0)
                remaining = maximum - used
            else:
                remaining = 0
                maximum = 0

            level_name = f"L{level}" if level > 0 else "C"
            text = f"{level_name}({remaining}/{maximum})"
            pill = QLabel(text)
            pill.setStyleSheet(
                "font-size: 10px; padding: 1px 4px; border-radius: 3px; "
                + ("opacity: 0.4;" if remaining <= 0 and level > 0 else "")
            )
            self._slot_layout.addWidget(pill)

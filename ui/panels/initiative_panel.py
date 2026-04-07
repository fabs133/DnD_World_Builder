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

    def __init__(self, parent=None, role: str = "dm"):
        super().__init__(parent)
        self._entries: list[dict] = []
        self._current_entity: str | None = None
        self._role = role  # "dm" or "player"
        self._viewer_entity_name: str = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Header
        self._header = QLabel("Initiative Tracker")
        self._header.setProperty("themeRole", "section-title")
        layout.addWidget(self._header)

        # Round indicator
        self._round_label = QLabel("Round: --")
        self._round_label.setProperty("themeRole", "hint")
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
        """Update HP display for a single entity, animating when possible.

        :param entity_name: Name of the entity.
        :param hp: Current HP.
        :param max_hp: Maximum HP.
        """
        for entry in self._entries:
            if entry["name"] == entity_name:
                entry["hp"] = hp
                entry["max_hp"] = max_hp
                break

        # Try to animate existing row instead of full rebuild
        for i in range(self._list.count()):
            item = self._list.item(i)
            row_widget = self._list.itemWidget(item)
            if isinstance(row_widget, _InitiativeRow) and row_widget.entity_name == entity_name:
                row_widget.animate_hp(hp, max_hp)
                return
        # Fallback: full rebuild if row not found
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

    def set_role(self, role: str, viewer_entity_name: str = "") -> None:
        """Set the viewing role for display filtering.

        :param role: ``"dm"`` (sees exact HP) or ``"player"`` (sees health category).
        :param viewer_entity_name: The player's entity name (for ``is_you`` highlighting).
        """
        self._role = role
        self._viewer_entity_name = viewer_entity_name
        self._next_btn.setVisible(role == "dm")
        self._rebuild_list()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _rebuild_list(self) -> None:
        self._list.clear()
        for entry in self._entries:
            item = QListWidgetItem()
            widget = _InitiativeRow(
                entry, role=self._role, viewer_name=self._viewer_entity_name,
            )
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

    def __init__(self, entry: dict, parent=None, role: str = "dm", viewer_name: str = ""):
        super().__init__(parent)
        self.entity_name = entry["name"]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        # Portrait thumbnail
        portrait_path = entry.get("portrait_path")
        if portrait_path:
            from PyQt5.QtGui import QPixmap
            pm = QPixmap(portrait_path)
            if not pm.isNull():
                portrait_label = QLabel()
                portrait_label.setFixedSize(28, 28)
                portrait_label.setPixmap(pm.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                portrait_label.setStyleSheet("border-radius: 14px;")
                layout.addWidget(portrait_label)

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
        if role == "player" and entry["name"] == viewer_name:
            name_text += "  (You)"
        self._name_label = QLabel(name_text)
        layout.addWidget(self._name_label, stretch=1)

        # HP display: DM sees exact HP bar, player sees health category
        hp = entry.get("hp")
        max_hp = entry.get("max_hp")
        health_category = entry.get("health_category")

        self._hp_bar: QProgressBar | None = None
        if role == "dm" and hp is not None and max_hp is not None and max_hp > 0:
            hp_bar = QProgressBar()
            hp_bar.setRange(0, max_hp)
            hp_bar.setValue(max(0, hp))
            hp_bar.setFormat(f"{hp}/{max_hp}")
            hp_bar.setMinimumWidth(60)
            hp_bar.setMaximumWidth(120)
            hp_bar.setFixedHeight(16)
            layout.addWidget(hp_bar)
            self._hp_bar = hp_bar
        elif role == "player" and health_category:
            cat_colors = {
                "healthy": "#3a6a2a",
                "wounded": "#7a6a20",
                "bloodied": "#8a2a2a",
                "near_death": "#a02020",
                "unconscious": "#444",
            }
            color = cat_colors.get(health_category, "#888")
            badge = QLabel(health_category.replace("_", " ").title())
            badge.setStyleSheet(
                f"color: white; background: {color}; "
                "border-radius: 3px; padding: 1px 6px; font-size: 11px;"
            )
            badge.setFixedHeight(18)
            layout.addWidget(badge)
        elif role == "dm":
            # No HP data — skip
            pass

    def animate_hp(self, new_hp: int, max_hp: int, duration_ms: int = 400) -> None:
        """Smoothly animate the HP bar value and update format text."""
        if not self._hp_bar:
            return
        self._hp_bar.setRange(0, max_hp)
        old_val = self._hp_bar.value()
        if old_val == new_hp:
            return
        from PyQt5.QtCore import QTimeLine
        import sip
        bar = self._hp_bar
        timeline = QTimeLine(duration_ms, self)
        timeline.setFrameRange(old_val, max(0, new_hp))

        def _step(frame: int) -> None:
            try:
                if not sip.isdeleted(bar):
                    bar.setValue(frame)
                    bar.setFormat(f"{frame}/{max_hp}")
            except RuntimeError:
                timeline.stop()

        timeline.frameChanged.connect(_step)
        timeline.start()

    def set_active(self, active: bool) -> None:
        """Toggle the active (current turn) highlight."""
        if active:
            self._name_label.setStyleSheet("font-weight: bold; color: #c084fc;")
        else:
            self._name_label.setStyleSheet("")

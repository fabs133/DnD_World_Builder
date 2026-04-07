"""Spell selection dialog for combat casting."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QScrollArea, QWidget, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal


class SpellSelectorDialog(QDialog):
    """Dialog for selecting a spell to cast during combat.

    Signals:
        spell_selected(dict): Emitted with spell data when player clicks Cast.
    """

    spell_selected = pyqtSignal(dict)

    def __init__(self, spells: list[dict], spell_slots: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cast a Spell")
        self.resize(500, 500)

        self._spells = spells
        self._spell_slots = spell_slots
        self._selected_spell: dict | None = None
        self._spell_cards: list[QFrame] = []

        layout = QVBoxLayout(self)

        # Tab widget for spell levels
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._build_tabs()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self._cast_btn = QPushButton("Cast")
        self._cast_btn.setEnabled(False)
        self._cast_btn.clicked.connect(self._on_cast)
        btn_row.addWidget(self._cast_btn)
        layout.addLayout(btn_row)

    def _build_tabs(self) -> None:
        # Group spells by level
        by_level: dict[int, list[dict]] = {}
        for spell in self._spells:
            level = spell.get("level", 0)
            by_level.setdefault(level, []).append(spell)

        # Cantrips first, then 1st through 9th
        all_levels = sorted(by_level.keys())

        for level in all_levels:
            spells = by_level[level]
            tab = self._create_tab(spells, level)

            if level == 0:
                label = "Cantrips"
            else:
                slot_info = self._spell_slots.get(level, {})
                if isinstance(slot_info, dict):
                    used = slot_info.get("used", 0)
                    maximum = slot_info.get("maximum", 0)
                    remaining = maximum - used
                    label = f"{self._ordinal(level)} ({remaining}/{maximum})"
                else:
                    label = self._ordinal(level)
                    remaining = 0

            self._tabs.addTab(tab, label)

            # Dim depleted tabs (but not cantrips)
            if level > 0:
                slot_info = self._spell_slots.get(level, {})
                if isinstance(slot_info, dict):
                    remaining = slot_info.get("maximum", 0) - slot_info.get("used", 0)
                    if remaining <= 0:
                        idx = self._tabs.count() - 1
                        self._tabs.tabBar().setTabTextColor(idx, Qt.gray)

    def _create_tab(self, spells: list[dict], level: int) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(6)

        for spell in spells:
            card = self._create_spell_card(spell, level)
            layout.addWidget(card)
            self._spell_cards.append(card)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _create_spell_card(self, spell: dict, level: int) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setCursor(Qt.PointingHandCursor)
        card.setProperty("spell_data", spell)
        card.setProperty("spell_level", level)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        name = QLabel(f"<b>{spell.get('name', 'Unknown')}</b>")
        layout.addWidget(name)

        school = spell.get("school", "")
        level_text = "cantrip" if level == 0 else f"{self._ordinal(level)}-level"
        if school:
            meta = QLabel(f"{school} {level_text}")
            meta.setStyleSheet("font-size: 11px; color: gray;")
            layout.addWidget(meta)

        details = []
        if "casting_time" in spell:
            details.append(f"Casting time: {spell['casting_time']}")
        if "range" in spell:
            details.append(f"Range: {spell['range']}")
        if details:
            detail_label = QLabel("  |  ".join(details))
            detail_label.setStyleSheet("font-size: 11px;")
            layout.addWidget(detail_label)

        desc = spell.get("desc", spell.get("description", ""))
        if isinstance(desc, list):
            desc = desc[0] if desc else ""
        if desc:
            short_desc = desc[:150] + "..." if len(desc) > 150 else desc
            desc_label = QLabel(short_desc)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("font-size: 11px; color: gray;")
            layout.addWidget(desc_label)

        card.mousePressEvent = lambda e, c=card: self._select_card(c)
        return card

    def _select_card(self, card: QFrame) -> None:
        # Clear previous selection
        for c in self._spell_cards:
            c.setStyleSheet("")

        spell = card.property("spell_data")
        level = card.property("spell_level")
        self._selected_spell = spell

        from core import theme_palette as tp
        card.setStyleSheet(f"border: 2px solid {tp.get_themed('accent_primary')};")

        # Enable cast if cantrip or slot available
        can_cast = False
        if level == 0:
            can_cast = True
        else:
            slot_info = self._spell_slots.get(level, {})
            if isinstance(slot_info, dict):
                remaining = slot_info.get("maximum", 0) - slot_info.get("used", 0)
                can_cast = remaining > 0

        self._cast_btn.setEnabled(can_cast)

    def _on_cast(self) -> None:
        if self._selected_spell:
            self.spell_selected.emit(self._selected_spell)
            self.accept()

    @staticmethod
    def _ordinal(n: int) -> str:
        suffixes = {1: "1st", 2: "2nd", 3: "3rd"}
        return suffixes.get(n, f"{n}th")

"""Inventory panel showing party items and gold during play."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame,
)
from PyQt5.QtCore import Qt

_HEADER_STYLE = (
    "font-size: 12px; font-weight: bold; color: #e8c840;"
    "padding: 4px 0 2px 0;"
)
_GOLD_STYLE = "font-size: 11px; color: #e8c840; padding-left: 8px;"
_ITEM_STYLE = "font-size: 11px; color: #d0c8b8; padding-left: 8px;"
_EMPTY_STYLE = "font-size: 11px; color: #807868; font-style: italic; padding-left: 8px;"
_TYPE_COLORS = {
    "weapon": "#c0392b",
    "armor": "#2980b9",
    "consumable": "#27ae60",
    "quest": "#e8c840",
    "trinket": "#95a5a6",
}


class InventoryPanel(QWidget):
    """Scrollable panel showing each party member's inventory and gold."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        self._content = QWidget()
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(2)
        self._layout.addStretch()
        scroll.setWidget(self._content)

    def refresh(self, entities) -> None:
        """Rebuild display from current entity list."""
        # Clear
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        players = [e for e in entities if getattr(e, "entity_type", "") == "player"]
        if not players:
            empty = QLabel("No party members")
            empty.setStyleSheet(_EMPTY_STYLE)
            self._layout.addWidget(empty)
            self._layout.addStretch()
            return

        for p in players:
            # Character header
            header = QLabel(p.name)
            header.setStyleSheet(_HEADER_STYLE)
            self._layout.addWidget(header)

            # Gold
            gold = p.stats.get("gold", 0)
            gold_lbl = QLabel(f"Gold: {gold} gp")
            gold_lbl.setStyleSheet(_GOLD_STYLE)
            self._layout.addWidget(gold_lbl)

            # Items
            inv = getattr(p, "inventory", [])
            if not inv:
                empty = QLabel("  (empty)")
                empty.setStyleSheet(_EMPTY_STYLE)
                self._layout.addWidget(empty)
            else:
                for item in inv:
                    if isinstance(item, dict):
                        name = item.get("name", "???")
                        itype = item.get("type", "trinket")
                        gv = item.get("gold_value", 0)
                        color = _TYPE_COLORS.get(itype, "#95a5a6")
                        text = (
                            f'<span style="color:{color};">[{itype}]</span> '
                            f'{name}'
                        )
                        if gv:
                            text += f' <span style="color:#e8c840;">({gv} gp)</span>'
                    else:
                        text = str(item)
                    lbl = QLabel(text)
                    lbl.setTextFormat(Qt.RichText)
                    lbl.setStyleSheet(_ITEM_STYLE)
                    self._layout.addWidget(lbl)

            # Separator
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet("color: rgba(200,170,100,40);")
            self._layout.addWidget(sep)

        self._layout.addStretch()

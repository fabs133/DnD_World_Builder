"""Compact party HP display for the exploration sidebar."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
)
from PyQt5.QtCore import pyqtSignal


class PartyStatusStrip(QWidget):
    """Minimal party status: name + HP bar for each player entity.

    Shown in the sidebar during exploration mode.

    Signals
    -------
    entity_selected(str)
        Emitted when a row is clicked (entity name).
    """

    entity_selected = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._rows: dict[str, dict] = {}
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(4)

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------

    def set_party(self, entries: list[dict]) -> None:
        """Rebuild the display from *entries*.

        Each dict: ``{"name": str, "hp": int, "max_hp": int}``.
        """
        self._clear_rows()
        for entry in entries:
            name = entry["name"]
            hp = entry.get("hp", 0)
            max_hp = entry.get("max_hp", hp) or 1

            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)

            label = QLabel(name)
            label.setMinimumWidth(50)
            label.setMaximumWidth(120)
            label.setStyleSheet("font-size: 11px;")
            row.addWidget(label)

            bar = QProgressBar()
            bar.setRange(0, max(1, max_hp))
            bar.setValue(max(0, min(hp, max_hp)))
            bar.setFormat(f"{hp}/{max_hp}")
            bar.setFixedHeight(16)
            bar.setTextVisible(True)
            bar.setStyleSheet(self._bar_style(hp, max_hp))
            row.addWidget(bar)

            gold = entry.get("gold", 0)
            gold_label = QLabel(f"{gold} gp")
            gold_label.setFixedWidth(50)
            gold_label.setStyleSheet(
                "font-size: 10px; color: #e8c840; font-weight: bold;")
            row.addWidget(gold_label)

            container.mousePressEvent = (
                lambda ev, n=name: self.entity_selected.emit(n)
            )

            self._layout.addWidget(container)
            self._rows[name] = {
                "container": container,
                "label": label,
                "bar": bar,
                "gold_label": gold_label,
                "max_hp": max_hp,
            }

    def update_entity_hp(self, entity_name: str, hp: int, max_hp: int) -> None:
        """Update a single row without rebuilding."""
        if entity_name not in self._rows:
            return
        row = self._rows[entity_name]
        bar: QProgressBar = row["bar"]
        bar.setRange(0, max(1, max_hp))
        bar.setValue(max(0, min(hp, max_hp)))
        bar.setFormat(f"{hp}/{max_hp}")
        bar.setStyleSheet(self._bar_style(hp, max_hp))

    def clear(self) -> None:
        self._clear_rows()

    # ----------------------------------------------------------
    # Internals
    # ----------------------------------------------------------

    def _clear_rows(self) -> None:
        for data in self._rows.values():
            data["container"].setParent(None)
            data["container"].deleteLater()
        self._rows.clear()

    @staticmethod
    def _bar_style(hp: int, max_hp: int) -> str:
        pct = hp / max_hp if max_hp > 0 else 0
        if pct > 0.5:
            colour = "#4caf50"
        elif pct > 0.25:
            colour = "#e8b84b"
        else:
            colour = "#c0392b"
        return (
            f"QProgressBar::chunk {{ background: {colour}; }}"
            f"QProgressBar {{ font-size: 10px; }}"
        )

"""Structured combat log with colour-coded, expandable entries.

Replaces the plain ``QTextEdit`` combat log with rich per-action
cards that show dice rolls, colour-code outcomes, and expand on click
to reveal the full execution log.
"""

from __future__ import annotations

import re
from typing import List

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy,
)

from core.theme_palette import palette

MAX_ENTRIES = 200

# ── Colour map ────────────────────────────────────────────────────────

_BORDER_COLORS: dict[str, str] = {
    "success":  "#2a6a30",
    "failure":  "#8a2020",
    "crit":     "#c9952a",
    "movement": "#2a5a8a",
    "system":   "#6b5a3e",
    "explore":  "#4a7a4a",
}

# Regex for highlighting dice expressions in log lines
_DICE_RE = re.compile(
    r"(d20)\((\d+)\)"           # d20(14)
    r"|(\d+d\d+(?:[+-]\d+)?)"  # 2d6+3
    r"|( = \d+)"               # = 18
    r"|((?:natural|nat)\s*(?:20|1))"  # natural 20, nat 1
    r"|(→\s*(?:HIT|MISS|CRIT))"     # → HIT etc.
    r"|((?:HIT|MISS|CRIT)!?)",       # standalone HIT / MISS / CRIT
    re.IGNORECASE,
)


def _highlight_dice(text: str) -> str:
    """Wrap dice expressions in coloured HTML spans."""

    def _repl(m: re.Match) -> str:
        full = m.group(0)
        low = full.lower()
        if "crit" in low or "natural 20" in low or "nat 20" in low:
            return f"<span style='color:#c9952a; font-weight:bold'>{full}</span>"
        if "miss" in low:
            return f"<span style='color:#8a2020'>{full}</span>"
        if "hit" in low:
            return f"<span style='color:#2a6a30; font-weight:bold'>{full}</span>"
        if full.startswith("d20"):
            roll_val = m.group(2)
            if roll_val == "20":
                return f"<span style='color:#c9952a; font-weight:bold'>d20({roll_val})</span>"
            if roll_val == "1":
                return f"<span style='color:#8a2020; font-weight:bold'>d20({roll_val})</span>"
            return f"<span style='color:#2a5a8a'>d20({roll_val})</span>"
        if " = " in full:
            return f"<b>{full}</b>"
        # Generic dice expression (2d6+3 etc.)
        return f"<span style='color:#2a5a8a'>{full}</span>"

    return _DICE_RE.sub(_repl, text)


# ── CombatLogEntry ────────────────────────────────────────────────────

class CombatLogEntry(QFrame):
    """Single expandable log entry with colour-coded border."""

    def __init__(
        self,
        actor_name: str,
        action_type: str,
        success: bool,
        execution_log: List[str],
        round_num: int = 0,
        is_ai: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._expanded = False
        self._execution_log = execution_log

        # Determine border colour
        summary_lower = " ".join(execution_log).lower()
        if "crit" in summary_lower:
            border = _BORDER_COLORS["crit"]
        elif success:
            border = _BORDER_COLORS["success"]
        else:
            border = _BORDER_COLORS["failure"]

        p = palette()
        self.setStyleSheet(
            f"CombatLogEntry {{"
            f"  background: {p['bg_input']};"
            f"  border-left: 3px solid {border};"
            f"  border-radius: 2px;"
            f"  padding: 4px 6px;"
            f"  margin: 1px 0px;"
            f"}}"
        )
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        # Header line: actor + action + round
        header = QHBoxLayout()
        header.setSpacing(6)

        actor_lbl = QLabel(f"<b>{actor_name}</b>")
        actor_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        actor_lbl.setStyleSheet(f"color: {p['text_primary']}; padding: 0;")
        header.addWidget(actor_lbl)

        action_lbl = QLabel(action_type)
        action_lbl.setFont(QFont("Segoe UI", 9))
        action_lbl.setStyleSheet(f"color: {p['text_secondary']}; padding: 0;")
        header.addWidget(action_lbl)

        header.addStretch()

        if round_num > 0:
            round_lbl = QLabel(f"R{round_num}")
            round_lbl.setFont(QFont("Segoe UI", 8))
            round_lbl.setStyleSheet(f"color: {p['text_tertiary']}; padding: 0;")
            header.addWidget(round_lbl)

        status_text = "OK" if success else "FAIL"
        status_color = _BORDER_COLORS["success"] if success else _BORDER_COLORS["failure"]
        status_lbl = QLabel(status_text)
        status_lbl.setFont(QFont("Segoe UI", 8, QFont.Bold))
        status_lbl.setStyleSheet(f"color: {status_color}; padding: 0;")
        header.addWidget(status_lbl)

        layout.addLayout(header)

        # Summary line (first execution_log entry, if any)
        if execution_log:
            summary = _highlight_dice(execution_log[0])
            self._summary_lbl = QLabel(summary)
            self._summary_lbl.setTextFormat(Qt.RichText)
            self._summary_lbl.setFont(QFont("Consolas", 9))
            self._summary_lbl.setStyleSheet(f"color: {p['text_secondary']}; padding: 0;")
            self._summary_lbl.setWordWrap(True)
            layout.addWidget(self._summary_lbl)

        # Detail lines (hidden by default)
        self._detail_widget = QWidget()
        detail_layout = QVBoxLayout(self._detail_widget)
        detail_layout.setContentsMargins(8, 2, 0, 0)
        detail_layout.setSpacing(1)
        for line in execution_log[1:]:
            lbl = QLabel(_highlight_dice(line))
            lbl.setTextFormat(Qt.RichText)
            lbl.setFont(QFont("Consolas", 8))
            lbl.setStyleSheet(f"color: {p['text_tertiary']}; padding: 0;")
            lbl.setWordWrap(True)
            detail_layout.addWidget(lbl)
        self._detail_widget.setVisible(False)
        layout.addWidget(self._detail_widget)

    def mousePressEvent(self, event) -> None:
        if self._execution_log and len(self._execution_log) > 1:
            self._expanded = not self._expanded
            self._detail_widget.setVisible(self._expanded)
        super().mousePressEvent(event)


class _SystemMessage(QLabel):
    """Lightweight label for non-combat log entries."""

    def __init__(self, text: str, style: str = "info", parent: QWidget | None = None):
        super().__init__(parent)
        p = palette()
        colour = {
            "info": p["text_tertiary"],
            "combat": _BORDER_COLORS["crit"],
            "explore": _BORDER_COLORS["explore"],
        }.get(style, p["text_tertiary"])
        self.setText(text)
        self.setFont(QFont("Segoe UI", 9))
        self.setStyleSheet(f"color: {colour}; padding: 2px 4px;")
        self.setWordWrap(True)


# ── CombatLogWidget ───────────────────────────────────────────────────

class CombatLogWidget(QWidget):
    """Scrollable combat log with structured, expandable entries.

    Drop-in replacement for ``QTextEdit`` — exposes ``append(text)``
    for backward compatibility.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._log_layout = QVBoxLayout(self._container)
        self._log_layout.setContentsMargins(2, 2, 2, 2)
        self._log_layout.setSpacing(2)
        self._log_layout.addStretch()

        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll)

        self._entry_count = 0

    def verticalScrollBar(self):
        """Proxy for backward compatibility with QTextEdit API."""
        return self._scroll.verticalScrollBar()

    # ── Public API ──────────────────────────────────────────────────

    def add_entry(
        self,
        actor_name: str,
        action_type: str,
        success: bool,
        execution_log: list[str],
        round_num: int = 0,
        is_ai: bool = False,
    ) -> None:
        """Add a structured combat log entry."""
        entry = CombatLogEntry(
            actor_name=actor_name,
            action_type=action_type,
            success=success,
            execution_log=execution_log,
            round_num=round_num,
            is_ai=is_ai,
        )
        self._insert(entry)

    def add_system_message(self, text: str, style: str = "info") -> None:
        """Add a non-combat message (phase transitions, etc.)."""
        self._insert(_SystemMessage(text, style))

    def append(self, text: str) -> None:
        """Backward-compatible plain-text append."""
        text = text.strip()
        if text:
            self.add_system_message(text)

    def setReadOnly(self, _: bool) -> None:
        """No-op for backward compatibility with QTextEdit API."""

    def setFont(self, _: QFont) -> None:
        """No-op for backward compatibility with QTextEdit API."""

    def setPlaceholderText(self, _: str) -> None:
        """No-op for backward compatibility with QTextEdit API."""

    def clear(self) -> None:
        """Remove all entries."""
        while self._log_layout.count() > 1:  # keep the stretch
            item = self._log_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._entry_count = 0

    # ── Internal ────────────────────────────────────────────────────

    def _insert(self, widget: QWidget) -> None:
        # Insert before the trailing stretch
        idx = max(self._log_layout.count() - 1, 0)
        self._log_layout.insertWidget(idx, widget)
        self._entry_count += 1

        # Prune oldest entries
        while self._entry_count > MAX_ENTRIES:
            item = self._log_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
                self._entry_count -= 1

        # Auto-scroll to bottom
        QTimer.singleShot(0, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        vbar = self._scroll.verticalScrollBar()
        vbar.setValue(vbar.maximum())

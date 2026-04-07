"""Rich contextual tooltip widget for tiles and entities.

Displayed on hover over map tiles with a short delay.  The content
adapts to the viewer's role (DM sees exact stats, players see
health categories).
"""

from __future__ import annotations

from typing import Any

from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QApplication, QWidget,
)

from core.theme_palette import palette


# ── Health category (reused from InfoFilter logic) ──────────────────────

def _health_category(hp: int, max_hp: int) -> tuple[str, str]:
    """Return (label, colour_hex) for a health category."""
    if max_hp <= 0:
        return ("dead", "#6b5d47")
    ratio = hp / max_hp
    if hp <= 0:
        return ("unconscious", "#888888")
    if ratio > 0.75:
        return ("healthy", "#2a6a30")
    if ratio > 0.50:
        return ("wounded", "#8a6a10")
    if ratio > 0.25:
        return ("bloodied", "#c06020")
    return ("near death", "#8a2020")


class RichTooltipWidget(QFrame):
    """Floating tooltip positioned near the cursor.

    Create once and reuse — call :meth:`set_tile_content` or
    :meth:`set_entity_content` to swap the payload, then
    :meth:`show_at` to display.
    """

    MAX_WIDTH = 260

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setMaximumWidth(self.MAX_WIDTH)

        p = palette()
        self.setStyleSheet(
            f"RichTooltipWidget {{"
            f"  background: {p['bg_secondary']};"
            f"  border: 1px solid {p['border_primary']};"
            f"  border-radius: 4px;"
            f"  padding: 6px 8px;"
            f"}}"
        )

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(3)

        self._title = QLabel()
        self._title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self._title.setStyleSheet(f"color: {p['text_primary']}; padding: 0;")
        self._layout.addWidget(self._title)

        self._body = QLabel()
        self._body.setWordWrap(True)
        self._body.setFont(QFont("Segoe UI", 9))
        self._body.setStyleSheet(f"color: {p['text_secondary']}; padding: 0;")
        self._layout.addWidget(self._body)

        self._hp_bar: QProgressBar | None = None

    # ── Content setters ─────────────────────────────────────────────

    def set_tile_content(
        self,
        terrain: str,
        elevation: int,
        tags: list[str],
        entities: list[dict[str, Any]],
        role: str = "dm",
    ) -> None:
        """Populate with tile overview data."""
        self._clear_hp_bar()

        self._title.setText(f"{terrain.title()} Tile")

        parts: list[str] = []
        if elevation != 0:
            parts.append(f"Elevation: {elevation}")
        if tags:
            tag_str = ", ".join(str(t) for t in tags)
            parts.append(f"Tags: {tag_str}")
        if entities:
            names = [e.get("name", "?") for e in entities[:4]]
            label = ", ".join(names)
            if len(entities) > 4:
                label += f" (+{len(entities) - 4})"
            parts.append(f"Entities: {label}")
        elif not entities:
            parts.append("Empty")

        self._body.setText("\n".join(parts) if parts else "")
        self.adjustSize()

    def set_entity_content(
        self,
        name: str,
        entity_type: str,
        hp: int,
        max_hp: int,
        ac: int,
        conditions: list[str],
        role: str = "dm",
    ) -> None:
        """Populate with mini stat block for a single entity."""
        self._title.setText(f"{name}")

        p = palette()
        parts: list[str] = [f"Type: {entity_type}"]

        if role == "dm" or role == "spectator":
            parts.append(f"HP: {hp}/{max_hp}  AC: {ac}")
            self._show_hp_bar(hp, max_hp)
        else:
            cat, colour = _health_category(hp, max_hp)
            parts.append(f"Condition: <b style='color:{colour}'>{cat}</b>")
            self._clear_hp_bar()

        if conditions:
            parts.append(f"Status: {', '.join(conditions)}")

        self._body.setText("\n".join(parts))
        self.adjustSize()

    # ── Positioning ─────────────────────────────────────────────────

    def show_at(self, global_pos: QPoint) -> None:
        """Show the tooltip near *global_pos*, clamped to screen."""
        offset = QPoint(16, 16)
        target = global_pos + offset

        screen = QApplication.screenAt(global_pos)
        if screen:
            geom = screen.availableGeometry()
            if target.x() + self.width() > geom.right():
                target.setX(global_pos.x() - self.width() - 8)
            if target.y() + self.height() > geom.bottom():
                target.setY(global_pos.y() - self.height() - 8)

        self.move(target)
        self.show()

    def hide_tooltip(self) -> None:
        self.hide()

    # ── Internal ────────────────────────────────────────────────────

    def _show_hp_bar(self, hp: int, max_hp: int) -> None:
        self._clear_hp_bar()
        bar = QProgressBar()
        bar.setRange(0, max(max_hp, 1))
        bar.setValue(max(hp, 0))
        bar.setTextVisible(False)
        bar.setFixedHeight(6)
        cat, colour = _health_category(hp, max_hp)
        bar.setStyleSheet(
            f"QProgressBar {{ background: #2a2a2a; border: none; border-radius: 2px; }}"
            f"QProgressBar::chunk {{ background: {colour}; border-radius: 2px; }}"
        )
        self._layout.addWidget(bar)
        self._hp_bar = bar

    def _clear_hp_bar(self) -> None:
        if self._hp_bar is not None:
            self._layout.removeWidget(self._hp_bar)
            self._hp_bar.deleteLater()
            self._hp_bar = None

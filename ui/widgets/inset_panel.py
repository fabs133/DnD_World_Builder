"""Inset panel frame with subtle bevel effect."""

from __future__ import annotations

from PyQt5.QtWidgets import QFrame, QWidget
from PyQt5.QtGui import QPainter, QPen, QColor, QLinearGradient
from PyQt5.QtCore import Qt

from core import theme_palette as tp


class InsetPanel(QFrame):
    """A QFrame that paints a subtle inset bevel border.

    Use as a drop-in replacement for QFrame anywhere you want a panel
    that looks recessed into the surface (side panels, info areas).
    Child widgets are laid out inside normally — just set a layout on it.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)

        pal = tp.palette()
        bg_top = QColor(pal.get("bg_secondary", "#faf4e4"))
        bg_bot = QColor(pal.get("bg_primary", "#f0e6cc"))
        border_light = QColor(pal.get("border_tertiary", "#d4be8a"))
        border_dark = QColor(pal.get("border_primary", "#b09060"))

        # Background gradient (subtle darkening top to bottom)
        grad = QLinearGradient(0, r.top(), 0, r.bottom())
        grad.setColorAt(0, bg_top)
        grad.setColorAt(1, bg_bot)
        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(r, 4, 4)

        # Top + left edge (lighter = raised above)
        p.setPen(QPen(border_light, 0.5))
        p.drawLine(r.topLeft().x() + 4, r.topLeft().y(),
                   r.topRight().x() - 4, r.topRight().y())
        p.drawLine(r.topLeft().x(), r.topLeft().y() + 4,
                   r.bottomLeft().x(), r.bottomLeft().y() - 4)

        # Bottom + right edge (darker = shadow below)
        p.setPen(QPen(border_dark, 0.5))
        p.drawLine(r.bottomLeft().x() + 4, r.bottomLeft().y(),
                   r.bottomRight().x() - 4, r.bottomRight().y())
        p.drawLine(r.topRight().x(), r.topRight().y() + 4,
                   r.bottomRight().x(), r.bottomRight().y() - 4)

        p.end()

        # Let QFrame paint children normally
        super().paintEvent(event)

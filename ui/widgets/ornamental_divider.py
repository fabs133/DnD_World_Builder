"""Decorative horizontal divider with a center diamond ornament."""

from __future__ import annotations

from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen, QColor, QPolygonF
from PyQt5.QtCore import Qt, QPointF

from core import theme_palette as tp


class OrnamentalDivider(QWidget):
    """A themed horizontal rule with a small diamond glyph at the center.

    Reads colors from :mod:`core.theme_palette` so it auto-updates on
    theme swap (caller should trigger ``update()`` via ``theme_changed``).
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(24)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        border_color = QColor(tp.get("border_secondary"))
        accent_color = QColor(tp.get("accent_primary"))
        mid_y = self.height() // 2
        mid_x = self.width() // 2
        margin = 24

        # Horizontal lines
        p.setPen(QPen(border_color, 0.5))
        p.drawLine(margin, mid_y, mid_x - 14, mid_y)
        p.drawLine(mid_x + 14, mid_y, self.width() - margin, mid_y)

        # Center diamond
        diamond = QPolygonF([
            QPointF(mid_x, mid_y - 6),
            QPointF(mid_x + 6, mid_y),
            QPointF(mid_x, mid_y + 6),
            QPointF(mid_x - 6, mid_y),
        ])
        p.setPen(QPen(accent_color, 0.5))
        p.setBrush(accent_color)
        p.drawPolygon(diamond)

        p.end()

"""Temporary visual effect overlays — slash lines, glow rings.

Self-destruct after animation completes.
"""

from __future__ import annotations
import math

from PyQt5.QtCore import QPointF, QRectF, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtWidgets import QGraphicsItem


class SlashEffect(QGraphicsItem):
    """Diagonal slash line that fades in then out, then self-removes."""

    def __init__(self, center: QPointF, size: float = 30.0,
                 color: str = "#e8b84b", duration_ms: int = 300,
                 parent: QGraphicsItem | None = None):
        super().__init__(parent)
        self._size = size
        self._color = QColor(color)
        self._duration = duration_ms
        self._elapsed = 0
        self._opacity = 0.0

        self.setPos(center)
        self.setZValue(998)

        half = size / 2
        self._bounds = QRectF(-half - 2, -half - 2, size + 4, size + 4)

        self._timer = QTimer()
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def play(self) -> None:
        self._elapsed = 0
        self._timer.start()

    def _tick(self) -> None:
        self._elapsed += 16
        t = min(1.0, self._elapsed / self._duration)

        # Fade in first half, fade out second half
        if t < 0.5:
            self._opacity = t * 2.0
        else:
            self._opacity = (1.0 - t) * 2.0

        if t >= 1.0:
            self._timer.stop()
            scene = self.scene()
            if scene:
                scene.removeItem(self)
            return

        self.update()

    def boundingRect(self) -> QRectF:
        return self._bounds

    def paint(self, painter: QPainter, option, widget=None) -> None:
        half = self._size / 2
        pen = QPen(self._color)
        pen.setWidthF(3.0)
        self._color.setAlphaF(self._opacity)
        pen.setColor(self._color)
        painter.setPen(pen)
        painter.drawLine(
            QPointF(-half, -half),
            QPointF(half, half),
        )


class GlowRing(QGraphicsItem):
    """Expanding ring that fades out, then self-removes."""

    def __init__(self, center: QPointF, max_radius: float = 25.0,
                 color: str = "#e8b84b", duration_ms: int = 400,
                 parent: QGraphicsItem | None = None):
        super().__init__(parent)
        self._max_radius = max_radius
        self._color = QColor(color)
        self._duration = duration_ms
        self._elapsed = 0
        self._current_radius = 0.0
        self._opacity = 0.8

        self.setPos(center)
        self.setZValue(997)

        r = max_radius + 4
        self._bounds = QRectF(-r, -r, r * 2, r * 2)

        self._timer = QTimer()
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def play(self) -> None:
        self._elapsed = 0
        self._timer.start()

    def _tick(self) -> None:
        self._elapsed += 16
        t = min(1.0, self._elapsed / self._duration)

        self._current_radius = self._max_radius * t
        self._opacity = 0.8 * (1.0 - t)

        if t >= 1.0:
            self._timer.stop()
            scene = self.scene()
            if scene:
                scene.removeItem(self)
            return

        self.update()

    def boundingRect(self) -> QRectF:
        return self._bounds

    def paint(self, painter: QPainter, option, widget=None) -> None:
        if self._current_radius < 0.5:
            return
        color = QColor(self._color)
        color.setAlphaF(max(0.0, min(1.0, self._opacity)))
        pen = QPen(color)
        pen.setWidthF(2.0)
        painter.setPen(pen)
        painter.setBrush(0)  # No fill
        painter.drawEllipse(QPointF(0, 0), self._current_radius, self._current_radius)

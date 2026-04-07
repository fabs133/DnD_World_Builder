"""Floating text that rises and fades — damage numbers, MISS, DEFEATED."""

from __future__ import annotations
from PyQt5.QtWidgets import QGraphicsTextItem
from PyQt5.QtCore import QTimer, QPointF
from PyQt5.QtGui import QColor, QFont


class FloatingText(QGraphicsTextItem):
    """Temporary text that floats upward and fades, then self-removes."""

    def __init__(self, text: str, start_pos: QPointF,
                 color: str = "#c0392b", font_size: int = 14,
                 duration_ms: int = 800):
        super().__init__(text)
        self._start_pos = QPointF(start_pos)
        self._duration = duration_ms
        self._elapsed = 0
        self._rise_distance = 30.0

        self.setDefaultTextColor(QColor(color))
        self.setFont(QFont("Arial", font_size, QFont.Bold))
        self.setPos(start_pos)
        self.setZValue(1000)

        self._timer = QTimer()
        self._timer.setInterval(33)  # ~30fps
        self._timer.timeout.connect(self._tick)

    def play(self) -> None:
        self._elapsed = 0
        self._timer.start()

    def _tick(self) -> None:
        self._elapsed += 33
        t = min(1.0, self._elapsed / self._duration)

        # Rise
        new_y = self._start_pos.y() - self._rise_distance * t
        self.setPos(self._start_pos.x(), new_y)

        # Fade
        self.setOpacity(1.0 - t)

        if t >= 1.0:
            self._timer.stop()
            scene = self.scene()
            if scene:
                scene.removeItem(self)

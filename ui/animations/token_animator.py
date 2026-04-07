"""Token animation helpers — lunge, shake, recoil for CombatTileItems.

Uses QTimer frame stepping since CombatTileItem (QGraphicsRectItem)
is not a QGraphicsObject and cannot be targeted by QPropertyAnimation.

All tick functions guard against deleted C++ objects via ``sip.isdeleted()``
to prevent crashes when combat scenes are torn down mid-animation.
"""

from __future__ import annotations
import math
import sip
from PyQt5.QtCore import QTimer, QPointF


class TokenAnimator:
    """Static methods that animate CombatTileItem position."""

    @staticmethod
    def lunge(tile_item, target_pos: QPointF, duration_ms: int = 300,
              distance_fraction: float = 0.3, callback=None) -> None:
        """Move tile toward target then back."""
        origin = QPointF(tile_item.pos())
        dx = target_pos.x() - origin.x()
        dy = target_pos.y() - origin.y()
        dist = math.hypot(dx, dy)
        if dist < 1:
            if callback:
                callback()
            return

        peak_x = origin.x() + dx * distance_fraction
        peak_y = origin.y() + dy * distance_fraction
        half = duration_ms // 2
        elapsed = [0]

        timer = QTimer()
        timer.setInterval(16)

        def tick():
            if sip.isdeleted(tile_item):
                timer.stop()
                return
            elapsed[0] += 16
            if elapsed[0] <= half:
                t = elapsed[0] / half
                tile_item.setPos(
                    origin.x() + (peak_x - origin.x()) * t,
                    origin.y() + (peak_y - origin.y()) * t,
                )
            elif elapsed[0] <= duration_ms:
                t = (elapsed[0] - half) / half
                tile_item.setPos(
                    peak_x + (origin.x() - peak_x) * t,
                    peak_y + (origin.y() - peak_y) * t,
                )
            else:
                timer.stop()
                tile_item.setPos(origin)
                if callback:
                    callback()

        timer.timeout.connect(tick)
        tile_item._anim_timer = timer  # prevent GC
        timer.start()

    @staticmethod
    def shake(tile_item, duration_ms: int = 200, amplitude: float = 4.0,
              callback=None) -> None:
        """Rapid horizontal oscillation."""
        origin = QPointF(tile_item.pos())
        elapsed = [0]

        timer = QTimer()
        timer.setInterval(16)

        def tick():
            if sip.isdeleted(tile_item):
                timer.stop()
                return
            elapsed[0] += 16
            t = elapsed[0] / duration_ms
            if t >= 1.0:
                timer.stop()
                tile_item.setPos(origin)
                if callback:
                    callback()
                return
            # Damped sine wave
            offset = amplitude * math.sin(t * math.pi * 6) * (1.0 - t)
            tile_item.setPos(origin.x() + offset, origin.y())

        timer.timeout.connect(tick)
        tile_item._anim_timer = timer
        timer.start()

    @staticmethod
    def recoil(tile_item, source_pos: QPointF, duration_ms: int = 200,
               distance: float = 8.0, callback=None) -> None:
        """Push away from source then snap back."""
        origin = QPointF(tile_item.pos())
        dx = origin.x() - source_pos.x()
        dy = origin.y() - source_pos.y()
        dist = math.hypot(dx, dy)
        if dist < 1:
            dx, dy = 1, 0
            dist = 1
        nx, ny = dx / dist, dy / dist
        peak_x = origin.x() + nx * distance
        peak_y = origin.y() + ny * distance
        half = duration_ms // 2
        elapsed = [0]

        timer = QTimer()
        timer.setInterval(16)

        def tick():
            if sip.isdeleted(tile_item):
                timer.stop()
                return
            elapsed[0] += 16
            if elapsed[0] <= half:
                t = elapsed[0] / half
                tile_item.setPos(
                    origin.x() + (peak_x - origin.x()) * t,
                    origin.y() + (peak_y - origin.y()) * t,
                )
            elif elapsed[0] <= duration_ms:
                t = (elapsed[0] - half) / half
                tile_item.setPos(
                    peak_x + (origin.x() - peak_x) * t,
                    peak_y + (origin.y() - peak_y) * t,
                )
            else:
                timer.stop()
                tile_item.setPos(origin)
                if callback:
                    callback()

        timer.timeout.connect(tick)
        tile_item._anim_timer = timer
        timer.start()

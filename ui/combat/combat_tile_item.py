"""Combat grid tile with elevation-based visual offset."""

from __future__ import annotations

from PyQt5.QtWidgets import QGraphicsRectItem
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont, QPolygonF, QPixmap
from PyQt5.QtCore import QRectF, QPointF, Qt, QTimer

from models.combat.elevation import ELEVATION_PX


class CombatTileItem(QGraphicsRectItem):
    """A single tile in the combat grid with elevation rendering.

    Higher tiles render higher on screen via a visual y-offset.
    A "side face" below elevated tiles creates a 2.5D depth effect.
    """

    def __init__(
        self,
        col: int,
        row: int,
        tile_size: int = 48,
        elevation: int = 0,
        terrain_type: str = "floor",
        tags: list[str] | None = None,
        show_elevation_label: bool = False,
    ):
        self.col = col
        self.row = row
        self._tile_size = tile_size
        self._elevation = elevation
        self._terrain_type = terrain_type
        self._tags = tags or []
        self._show_label = show_elevation_label
        self._overlay_color: QColor | None = None
        self._token_name: str = ""
        self._token_faction: str = ""
        self._token_is_current: bool = False
        self._token_portrait: QPixmap | None = None
        self._bg_pixmap: QPixmap | None = None
        self._has_zones: bool = False
        self._conditions: list[str] = []
        self._pulse_color: QColor | None = None
        self._pulse_timer: QTimer | None = None

        side_height = max(0, elevation * ELEVATION_PX)
        visual_y = row * tile_size - (elevation * ELEVATION_PX)

        super().__init__(
            col * tile_size,
            visual_y,
            tile_size,
            tile_size + side_height,
        )

        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)

    @property
    def elevation(self) -> int:
        return self._elevation

    def set_elevation(self, elevation: int) -> None:
        self._elevation = elevation
        side_height = max(0, elevation * ELEVATION_PX)
        visual_y = self.row * self._tile_size - (elevation * ELEVATION_PX)
        self.setRect(
            self.col * self._tile_size,
            visual_y,
            self._tile_size,
            self._tile_size + side_height,
        )
        self.update()

    def set_overlay(self, color: QColor, opacity: float = 0.3) -> None:
        color.setAlphaF(opacity)
        self._overlay_color = color
        self.update()

    def clear_overlay(self) -> None:
        self._overlay_color = None
        self.update()

    def set_token(self, entity_name: str, faction: str,
                  is_current_turn: bool = False,
                  portrait_path: str | None = None) -> None:
        self._token_name = entity_name
        self._token_faction = faction
        self._token_is_current = is_current_turn
        self._token_portrait = None
        if portrait_path:
            pm = QPixmap(portrait_path)
            if not pm.isNull():
                self._token_portrait = pm
        self.update()

    def clear_token(self) -> None:
        self._token_name = ""
        self._token_faction = ""
        self._token_is_current = False
        self._token_portrait = None
        self._conditions = []
        self.update()

    def set_background_image(self, path: str | None) -> None:
        """Set a terrain texture image for this tile."""
        self._bg_pixmap = None
        if path:
            pm = QPixmap(path)
            if not pm.isNull():
                self._bg_pixmap = pm
        self.update()

    # Condition icon map: condition_name → (unicode symbol, colour hex)
    _CONDITION_ICONS: dict[str, tuple[str, str]] = {
        "poisoned":       ("\u2620", "#2ecc71"),
        "stunned":        ("\u2744", "#3498db"),
        "frightened":     ("\u2623", "#9b59b6"),
        "blinded":        ("\u25cf", "#7f8c8d"),
        "prone":          ("\u2193", "#e67e22"),
        "restrained":     ("\u26d3", "#e74c3c"),
        "paralyzed":      ("\u26a1", "#f1c40f"),
        "concentrating":  ("\u2726", "#3498db"),
        "invisible":      ("\u25cb", "#bdc3c7"),
        "charmed":        ("\u2665", "#e91e63"),
    }

    def set_conditions(self, conditions: list[str]) -> None:
        """Set active conditions to display as small icons below the token."""
        self._conditions = conditions
        self.update()

    def pulse_select(self, color: QColor | None = None,
                     duration_ms: int = 400) -> None:
        """Flash a coloured overlay that fades out, indicating selection."""
        self._pulse_color = QColor(color or QColor(220, 180, 40, 80))
        self._pulse_elapsed = 0
        self._pulse_duration = duration_ms
        if self._pulse_timer is None:
            self._pulse_timer = QTimer()
            self._pulse_timer.timeout.connect(self._pulse_tick)
        self._pulse_timer.start(33)

    def _pulse_tick(self) -> None:
        self._pulse_elapsed = getattr(self, '_pulse_elapsed', 0) + 33
        t = min(1.0, self._pulse_elapsed / self._pulse_duration)
        self._pulse_color.setAlphaF(0.3 * (1.0 - t))
        self.update()
        if t >= 1.0:
            self._pulse_timer.stop()
            self._pulse_color = None
            self.update()

    def paint(self, painter: QPainter, option, widget=None) -> None:
        ts = self._tile_size
        side_h = max(0, self._elevation * ELEVATION_PX)
        top_y = 0
        rect = self.rect()
        x = rect.x()
        y = rect.y()

        # Side face (if elevated)
        if side_h > 0:
            top_color = self._get_terrain_color()
            side_color = top_color.darker(130)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(side_color))
            painter.drawRect(QRectF(x, y + ts, ts, side_h))

        # Top face
        if self._bg_pixmap:
            painter.drawPixmap(
                QRectF(x, y, ts, ts).toRect(),
                self._bg_pixmap.scaled(
                    int(ts), int(ts),
                    Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation),
            )
            painter.setPen(QPen(QColor(60, 50, 40), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(QRectF(x, y, ts, ts))
        else:
            top_color = self._get_terrain_color()
            painter.setBrush(QBrush(top_color))
            painter.setPen(QPen(QColor(60, 50, 40), 1))
            painter.drawRect(QRectF(x, y, ts, ts))

        # Overlay
        if self._overlay_color:
            painter.setBrush(QBrush(self._overlay_color))
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(x, y, ts, ts))

        # Zone detail indicator (small gold diamond in bottom-right corner)
        if self._has_zones:
            ind = ts * 0.2
            cx = x + ts - ind / 2 - 3
            cy = y + ts - ind / 2 - 3
            half = ind / 2
            painter.setPen(QPen(QColor(220, 180, 40), 1))
            painter.setBrush(QBrush(QColor(220, 180, 40, 120)))
            painter.drawPolygon(QPolygonF([
                QPointF(cx, cy - half),
                QPointF(cx + half, cy),
                QPointF(cx, cy + half),
                QPointF(cx - half, cy),
            ]))

        # Entity token
        if self._token_name:
            cx = x + ts / 2
            cy = y + ts / 2
            radius = ts * 0.3

            if self._token_portrait:
                # Circular-clipped portrait
                from PyQt5.QtGui import QPainterPath as _PPath
                clip = _PPath()
                clip.addEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))
                painter.save()
                painter.setClipPath(clip)
                sz = int(radius * 2)
                painter.drawPixmap(
                    int(cx - radius), int(cy - radius), sz, sz,
                    self._token_portrait.scaled(sz, sz, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation),
                )
                painter.restore()
                # Border
                if self._token_is_current:
                    painter.setPen(QPen(QColor(220, 180, 40), 3))
                else:
                    painter.setPen(QPen(QColor(20, 20, 20), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))
            else:
                # Colored circle fallback
                faction_colors = {
                    "player": QColor(60, 100, 200),
                    "enemy": QColor(200, 60, 60),
                    "ally": QColor(60, 180, 60),
                    "neutral": QColor(140, 140, 140),
                }
                color = faction_colors.get(self._token_faction, QColor(140, 140, 140))
                if self._token_is_current:
                    painter.setPen(QPen(QColor(220, 180, 40), 3))
                else:
                    painter.setPen(QPen(QColor(20, 20, 20), 1))
                painter.setBrush(QBrush(color))
                painter.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))

        # Condition icons (below entity token)
        if self._token_name and self._conditions:
            icon_size = max(8, ts * 0.18)
            shown = self._conditions[:4]
            total_w = len(shown) * icon_size
            start_x = x + ts / 2 - total_w / 2
            icon_y = y + ts / 2 + ts * 0.3 + 2
            for i, cond in enumerate(shown):
                symbol, colour = self._CONDITION_ICONS.get(
                    cond.lower(), ("\u2022", "#ffffff"))
                painter.setPen(QPen(QColor(colour)))
                painter.setFont(QFont("Arial", int(icon_size)))
                painter.drawText(
                    QRectF(start_x + i * icon_size, icon_y,
                           icon_size, icon_size),
                    Qt.AlignCenter, symbol)

        # Selection pulse overlay
        if self._pulse_color is not None:
            painter.setBrush(QBrush(self._pulse_color))
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(x, y, ts, ts))

        # Elevation label (DM only)
        if self._show_label and self._elevation != 0:
            painter.setPen(QPen(QColor(200, 200, 200)))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(QRectF(x + 2, y + 2, ts - 4, 14), Qt.AlignLeft, str(self._elevation))

    def _get_terrain_color(self) -> QColor:
        if "blocks_movement" in [t.lower() if isinstance(t, str) else t for t in self._tags]:
            return QColor(50, 45, 40)
        # Terrain-type based colors
        terrain_colors = {
            "GRASS": QColor(100, 140, 75),
            "WATER": QColor(55, 95, 170),
            "MOUNTAIN": QColor(140, 130, 120),
            "FLOOR": QColor(150, 140, 125),
            "WALL": QColor(55, 50, 45),
            "SAND": QColor(190, 175, 130),
            "SWAMP": QColor(75, 100, 65),
        }
        tc = terrain_colors.get(self._terrain_type.upper() if isinstance(self._terrain_type, str) else "", None)
        if tc:
            return tc
        if self._elevation >= 3:
            return QColor(180, 170, 150)
        if self._elevation >= 1:
            return QColor(150, 140, 120)
        if self._elevation < 0:
            return QColor(40, 35, 30)
        return QColor(100, 95, 85)

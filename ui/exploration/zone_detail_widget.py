"""Zone exploration view with overlay HUD and depth-scaled NPC tokens."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal, QRectF
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont, QPixmap

from models.entities.entity_type import EntityType
from models.exploration.zone_scene_data import (
    ZoneSceneData, SceneObject, LAYER_HEIGHTS,
)

# Depth-based token sizing and vertical placement
_TOKEN_RADIUS = {1: 24, 2: 36, 3: 50}
_DEPTH_Y_RATIO = {1: 0.40, 2: 0.58, 3: 0.74}
_FACTION_COLORS = {
    "friendly": QColor(60, 180, 100),
    "hostile": QColor(200, 60, 60),
    "neutral": QColor(200, 160, 60),
}


# ── Canvas ────────────────────────────────────────────────────────────


class ZoneCanvas(QWidget):
    """Custom widget that paints the background and depth-scaled NPC tokens."""

    entity_clicked = pyqtSignal(str)

    _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene_data: ZoneSceneData | None = None
        self._highlighted: str = ""
        self._bg_pixmap: QPixmap | None = None
        self._bg_scaled: QPixmap | None = None  # cached scaled background
        self._bg_scaled_size: tuple[int, int] = (0, 0)
        self._portrait_cache: dict[str, QPixmap | None] = {}
        self.setMinimumSize(400, 300)

    def set_scene(self, data: ZoneSceneData) -> None:
        self._scene_data = data
        self._bg_pixmap = None
        self._bg_scaled = None
        self._bg_scaled_size = (0, 0)
        self._portrait_cache.clear()

        try:
            from core.asset_cache import AssetCache
            cache = AssetCache.instance()
        except Exception:
            cache = None

        if data and data.background_image:
            bg_path = self._PROJECT_ROOT / data.background_image
            if bg_path.exists():
                path_str = str(bg_path)
                if cache:
                    pm = cache.request(path_str, callback=self._on_bg_ready)
                    if pm is not None:
                        self._bg_pixmap = pm
                else:
                    self._bg_pixmap = QPixmap(path_str)

        if data:
            for depth_objs in data.objects_by_depth.values():
                for obj in depth_objs:
                    if obj.image_path and obj.name not in self._portrait_cache:
                        p = self._PROJECT_ROOT / obj.image_path
                        if p.exists():
                            p_str = str(p)
                            if cache:
                                pm = cache.request(p_str, callback=lambda path, px, n=obj.name: self._on_portrait_ready(n, px))
                                if pm is not None:
                                    self._portrait_cache[obj.name] = pm
                                else:
                                    self._portrait_cache[obj.name] = None  # pending
                            else:
                                self._portrait_cache[obj.name] = QPixmap(p_str)
                        else:
                            self._portrait_cache[obj.name] = None
        self.update()

    def _on_bg_ready(self, path: str, pixmap) -> None:
        """Called on GUI thread when background image loads from cache."""
        self._bg_pixmap = pixmap
        self._bg_scaled = None
        self._bg_scaled_size = (0, 0)
        self.update()

    def _on_portrait_ready(self, name: str, pixmap) -> None:
        """Called on GUI thread when a portrait loads from cache."""
        self._portrait_cache[name] = pixmap
        self.update()

    def highlight_entity(self, name: str) -> None:
        self._highlighted = name
        self.update()

    # ── painting ──────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        if not self._scene_data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Background — fit image fully within canvas, centered, with
        # dark fill on any letterbox bars.
        painter.fillRect(0, 0, w, h, QColor(30, 28, 24))
        if self._bg_pixmap and not self._bg_pixmap.isNull():
            if self._bg_scaled is None or self._bg_scaled_size != (w, h):
                self._bg_scaled = self._bg_pixmap.scaled(
                    w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._bg_scaled_size = (w, h)
            # Center the scaled image
            dx = (w - self._bg_scaled.width()) // 2
            dy = (h - self._bg_scaled.height()) // 2
            painter.drawPixmap(dx, dy, self._bg_scaled)

        # Compute image rect for token positioning (tokens sit on the image,
        # not the letterbox bars)
        if self._bg_scaled:
            img_w, img_h = self._bg_scaled.width(), self._bg_scaled.height()
            img_x = (w - img_w) // 2
            img_y = (h - img_h) // 2
        else:
            img_w, img_h, img_x, img_y = w, h, 0, 0

        # Paint objects back-to-front (depth 1 = far, 3 = near)
        for depth in (1, 2, 3):
            for obj in self._scene_data.objects_by_depth.get(depth, []):
                self._paint_token(painter, obj, img_w, img_h, depth,
                                  offset_x=img_x, offset_y=img_y)

        # Player token
        if self._scene_data.player_position:
            px, pd = self._scene_data.player_position
            cx = img_x + int(px * img_w)
            cy = img_y + int(img_h * 0.78)
            painter.setPen(QPen(QColor(220, 180, 40), 3))
            painter.setBrush(QBrush(QColor(60, 100, 200)))
            painter.drawEllipse(QRectF(cx - 14, cy - 14, 28, 28))

        painter.end()

    def _paint_token(self, painter: QPainter, obj: SceneObject,
                     w: int, h: int, depth: int,
                     offset_x: int = 0, offset_y: int = 0) -> None:
        cx = offset_x + int(obj.x_percent * w)
        cy = offset_y + int(h * _DEPTH_Y_RATIO.get(depth, 0.74))
        radius = _TOKEN_RADIUS.get(depth, 36)
        size = radius * 2
        faction_color = _FACTION_COLORS.get(obj.faction, QColor(140, 140, 140))

        portrait = self._portrait_cache.get(obj.name)
        if portrait and not portrait.isNull():
            from PyQt5.QtGui import QPainterPath
            clip = QPainterPath()
            clip.addEllipse(QRectF(cx - radius, cy - radius, size, size))
            painter.save()
            painter.setClipPath(clip)
            painter.drawPixmap(
                int(cx - radius), int(cy - radius), size, size,
                portrait.scaled(size, size, Qt.KeepAspectRatioByExpanding,
                                Qt.SmoothTransformation))
            painter.restore()
            # Faction-colored border
            if obj.name == self._highlighted:
                painter.setPen(QPen(QColor(220, 180, 40), 3))
            else:
                painter.setPen(QPen(faction_color, 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QRectF(cx - radius, cy - radius, size, size))
        else:
            # Fallback: colored circle with initials
            if obj.name == self._highlighted:
                painter.setPen(QPen(QColor(220, 180, 40), 3))
            else:
                painter.setPen(QPen(QColor(30, 30, 30), 1))
            painter.setBrush(QBrush(faction_color))
            painter.drawEllipse(QRectF(cx - radius, cy - radius, size, size))
            painter.setPen(QPen(QColor(255, 255, 255)))
            font_size = {1: 8, 2: 10, 3: 14}.get(depth, 10)
            painter.setFont(QFont("Arial", font_size, QFont.Bold))
            painter.drawText(
                QRectF(cx - radius, cy - radius, size, size),
                Qt.AlignCenter, obj.initials)

        # Name plate with pill background
        font_size = 9 if depth == 3 else 8
        label_w = max(80, radius * 3)
        label_rect = QRectF(cx - label_w / 2, cy + radius + 4, label_w, 18)
        painter.setBrush(QBrush(QColor(0, 0, 0, 160)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(label_rect, 4, 4)
        painter.setPen(QPen(QColor(255, 255, 255, 230)))
        painter.setFont(QFont("Arial", font_size))
        painter.drawText(label_rect, Qt.AlignCenter, obj.name)

    # ── interaction ───────────────────────────────────────────────

    def mousePressEvent(self, event):
        if not self._scene_data:
            return
        x, y = event.x(), event.y()
        w, h = self.width(), self.height()

        # Match the same image-rect logic as paintEvent so click targets
        # align with drawn tokens (accounts for letterbox offset)
        if self._bg_scaled:
            img_w, img_h = self._bg_scaled.width(), self._bg_scaled.height()
            img_x = (w - img_w) // 2
            img_y = (h - img_h) // 2
        else:
            img_w, img_h, img_x, img_y = w, h, 0, 0

        for depth in (3, 2, 1):
            radius = _TOKEN_RADIUS.get(depth, 36)
            for obj in self._scene_data.objects_by_depth.get(depth, []):
                cx = img_x + int(obj.x_percent * img_w)
                cy = img_y + int(img_h * _DEPTH_Y_RATIO.get(depth, 0.74))
                if abs(x - cx) < radius and abs(y - cy) < radius:
                    self.entity_clicked.emit(obj.name)
                    return


# ── Overlay widgets ───────────────────────────────────────────────────


class _OverlayBar(QWidget):
    """Semi-transparent breadcrumb bar at top of canvas."""

    navigate_to_map = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "background: rgba(0,0,0,140);"
            "border-bottom: 1px solid rgba(255,255,255,30);")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 2, 8, 2)
        self._map_btn = QPushButton("World Map")
        self._map_btn.setFlat(True)
        self._map_btn.setStyleSheet("color: #aaa; font-size: 11px;")
        self._map_btn.clicked.connect(self.navigate_to_map.emit)
        lay.addWidget(self._map_btn)
        sep = QLabel(" / ")
        sep.setStyleSheet("color: #666; font-size: 11px;")
        lay.addWidget(sep)
        self._zone_label = QLabel("--")
        self._zone_label.setStyleSheet(
            "color: #ddd; font-weight: bold; font-size: 12px;")
        lay.addWidget(self._zone_label)
        lay.addStretch()


class _OverlayEntitySidebar(QWidget):
    """Collapsible entity list on the right edge."""

    entity_clicked = pyqtSignal(object)
    entity_info_requested = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = False
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Toggle tab
        self._toggle_btn = QPushButton("Entities")
        self._toggle_btn.setFixedWidth(28)
        self._toggle_btn.setStyleSheet(
            "QPushButton { background: rgba(0,0,0,160); color: #ccc;"
            "  border: 1px solid rgba(255,255,255,30);"
            "  border-radius: 4px; font-size: 9px; padding: 4px 2px; }"
            "QPushButton:hover { background: rgba(0,0,0,200); }")
        self._toggle_btn.clicked.connect(self._toggle)
        lay.addWidget(self._toggle_btn)

        # Entity list
        self._entity_list = QListWidget()
        self._entity_list.setStyleSheet(
            "QListWidget { background: rgba(30,28,26,200);"
            "  border: 1px solid rgba(255,255,255,30); border-radius: 4px; }"
            "QListWidget::item { padding: 3px 6px; color: #ccc; }"
            "QListWidget::item:selected { background: rgba(60,55,50,200); }")
        self._entity_list.itemClicked.connect(self._on_item_clicked)
        self._entity_list.hide()
        lay.addWidget(self._entity_list)

    def _toggle(self):
        self._expanded = not self._expanded
        self._entity_list.setVisible(self._expanded)
        self._toggle_btn.setText("<" if self._expanded else "Entities")
        # Trigger parent resize to reposition
        if self.parent():
            self.parent().update()

    def _on_item_clicked(self, item: QListWidgetItem):
        entity = item.data(Qt.UserRole)
        if entity is not None:
            self.entity_clicked.emit(entity)
            name = getattr(entity, "name", str(entity))
            etype = getattr(entity, "entity_type", "")
            self.entity_info_requested.emit(name, etype)


class _OverlayNavArrows(QWidget):
    """Navigation arrow buttons placed directly on the parent canvas.

    Instead of a full-area overlay (which blocks mouse events), the buttons
    are parented directly and repositioned by the parent's resizeEvent.
    """

    navigate_to_zone = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hide()  # This widget itself is invisible; buttons parent to _parent
        self._buttons: list[QPushButton] = []
        self._parent_ref = parent

    def set_arrows(self, nav_arrows):
        for btn, _dir in self._buttons:
            btn.hide()
            btn.setParent(None)
            btn.deleteLater()
        self._buttons.clear()

        if not nav_arrows:
            return

        _btn_style = (
            "QPushButton { background: rgba(0,0,0,160); color: #ddd;"
            "  border: 1px solid rgba(255,255,255,40); border-radius: 6px;"
            "  font-size: 11px; padding: 6px 10px; }"
            "QPushButton:hover { background: rgba(0,0,0,220); }"
            "QPushButton:disabled { color: #666; background: rgba(0,0,0,100); }")

        _dir_arrows = {"up": "\u2191", "down": "\u2193", "left": "\u2190", "right": "\u2192"}

        target = self._parent_ref or self.parent()
        for arrow in nav_arrows:
            prefix = _dir_arrows.get(arrow.direction, "")
            label = f" {prefix} {arrow.target_label} " if prefix else f"  {arrow.target_label}  "
            btn = QPushButton(label, target)
            btn.setStyleSheet(_btn_style)
            if arrow.locked:
                btn.setEnabled(False)
                btn.setToolTip(f"Locked: {arrow.lock_description}")
            else:
                btn.clicked.connect(
                    lambda checked, zid=arrow.target_zone_id:
                        self.navigate_to_zone.emit(zid))
            btn.adjustSize()
            btn.show()
            btn.raise_()
            self._buttons.append((btn, arrow.direction))

    def reposition(self, w: int, h: int):
        """Place nav buttons on screen edges matching their direction."""
        if not self._buttons:
            return

        margin = 12

        # Group buttons by direction
        by_dir: dict[str, list[QPushButton]] = {}
        for btn, direction in self._buttons:
            by_dir.setdefault(direction, []).append(btn)

        for direction, btns in by_dir.items():
            if direction == "up":
                # Top-center, side by side
                total_w = sum(b.width() for b in btns) + 6 * (len(btns) - 1)
                x = (w - total_w) // 2
                for btn in btns:
                    btn.move(x, 40)  # below breadcrumb bar
                    btn.raise_()
                    x += btn.width() + 6
            elif direction == "down":
                # Bottom-center
                total_w = sum(b.width() for b in btns) + 6 * (len(btns) - 1)
                x = (w - total_w) // 2
                for btn in btns:
                    btn.move(x, h - btn.height() - margin)
                    btn.raise_()
                    x += btn.width() + 6
            elif direction == "left":
                # Left-center, stacked vertically
                total_h = sum(b.height() for b in btns) + 6 * (len(btns) - 1)
                y = (h - total_h) // 2
                for btn in btns:
                    btn.move(margin, y)
                    btn.raise_()
                    y += btn.height() + 6
            elif direction == "right":
                # Right-center, stacked vertically
                total_h = sum(b.height() for b in btns) + 6 * (len(btns) - 1)
                y = (h - total_h) // 2
                for btn in btns:
                    btn.move(w - btn.width() - margin, y)
                    btn.raise_()
                    y += btn.height() + 6
            else:
                # Unknown direction — bottom-center fallback
                total_w = sum(b.width() for b in btns) + 6 * (len(btns) - 1)
                x = (w - total_w) // 2
                for btn in btns:
                    btn.move(x, h - btn.height() - margin)
                    btn.raise_()
                    x += btn.width() + 6


# ── Main widget ───────────────────────────────────────────────────────


class ZoneDetailWidget(QWidget):
    """Zone exploration view with overlay HUD.

    Signals:
        navigate_to_zone(str): Player wants to move to another zone.
        navigate_to_map(): Player wants to return to world map.
        entity_clicked(object): Player clicked an NPC/object token.
        entity_interaction(str, str): Player chose an interaction.
    """

    navigate_to_zone = pyqtSignal(str)
    navigate_to_map = pyqtSignal()
    navigate_direction = pyqtSignal(int, int)
    entity_clicked = pyqtSignal(object)
    entity_interaction = pyqtSignal(str, str)
    entity_info_requested = pyqtSignal(str, str)

    _TYPE_COLORS = {
        "player": "#4a90d9", "enemy": "#d94a4a", "monster": "#d94a4a",
        "hostile": "#d94a4a", "npc": "#4ad97a", "ally": "#4ad97a",
        "companion": "#4ad97a",
    }

    def __init__(self, role: str = "player", parent=None):
        super().__init__(parent)
        self._role = role
        self._scene_data: ZoneSceneData | None = None

        # Canvas fills entire widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._canvas = ZoneCanvas()
        self._canvas.entity_clicked.connect(
            lambda name: self.entity_clicked.emit(name))
        layout.addWidget(self._canvas)

        # ── Overlay widgets (parented to self, positioned in resizeEvent) ──

        # Breadcrumb bar (top)
        self._breadcrumb_bar = _OverlayBar(parent=self)
        self._breadcrumb_bar.navigate_to_map.connect(self.navigate_to_map.emit)

        # Entity sidebar (right edge, collapsed by default)
        self._entity_sidebar = _OverlayEntitySidebar(parent=self)
        self._entity_sidebar.entity_clicked.connect(self._on_list_entity_clicked)
        self._entity_sidebar.entity_info_requested.connect(
            self.entity_info_requested.emit)
        self._entity_sidebar.hide()  # redundant with dock panel system

        # Nav arrows overlay
        self._nav_overlay = _OverlayNavArrows(parent=self)
        self._nav_overlay.navigate_to_zone.connect(self.navigate_to_zone.emit)

        # NPC interaction panel (overlay, hidden)
        from ui.exploration.npc_interaction_panel import NpcInteractionPanel
        self._npc_panel = NpcInteractionPanel(parent=self)
        self._npc_panel.setStyleSheet(
            "NpcInteractionPanel { background: rgba(30,28,26,210);"
            "  border: 1px solid rgba(255,255,255,40); border-radius: 6px; }")
        self._npc_panel.hide()

        # Status label (bottom-left)
        self._status = QLabel("Arrow keys to move, click NPCs to interact",
                              parent=self)
        self._status.setStyleSheet(
            "color: rgba(200,200,200,180); font-style: italic;"
            "padding: 4px 8px; background: rgba(0,0,0,120); border-radius: 4px;")

        # Floating info toast (for inspect results, auto-dismiss)
        self._info_toast = QLabel(self)
        self._info_toast.setWordWrap(True)
        self._info_toast.setStyleSheet(
            "background: rgba(20, 18, 16, 220);"
            "color: #e0d8c8; font-size: 13px; padding: 12px 16px;"
            "border: 1px solid rgba(200, 170, 100, 80); border-radius: 8px;")
        self._info_toast.hide()
        self._info_toast_timer = None

        self.setFocusPolicy(Qt.StrongFocus)

        # Crossfade state (timer-driven, no QGraphicsOpacityEffect)
        self._fade_alpha = 0.0
        self._fade_direction = 0  # 0=idle, 1=fading in, -1=fading out
        self._fade_timer = None

    def _crossfade_content(self) -> None:
        """Dim through a painted overlay to smooth content swaps.

        Uses a simple QTimer + paintEvent overlay instead of
        QGraphicsOpacityEffect, avoiding QPainter conflicts.
        """
        from PyQt5.QtCore import QTimer

        # If already fading, just restart
        if self._fade_timer is not None:
            self._fade_timer.stop()

        self._fade_alpha = 0.0
        self._fade_direction = 1  # fading in
        self._fade_timer = QTimer(self)
        self._fade_timer.timeout.connect(self._fade_tick)
        self._fade_timer.start(16)  # ~60fps

    def _fade_tick(self) -> None:
        step = 0.08 if self._fade_direction == 1 else 0.05
        self._fade_alpha += step * self._fade_direction

        if self._fade_direction == 1 and self._fade_alpha >= 0.7:
            self._fade_alpha = 0.7
            self._fade_direction = -1  # start fading out
        elif self._fade_direction == -1 and self._fade_alpha <= 0.0:
            self._fade_alpha = 0.0
            self._fade_direction = 0
            if self._fade_timer:
                self._fade_timer.stop()
                self._fade_timer = None

        self.update()  # triggers paintEvent on ZoneDetailWidget

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._fade_alpha > 0.0:
            painter = QPainter(self)
            painter.fillRect(
                self._canvas.geometry(),
                QColor(24, 22, 20, int(self._fade_alpha * 255)))
            painter.end()

    # ── Backward-compatible accessors ─────────────────────────────

    @property
    def _zone_label(self):
        return self._breadcrumb_bar._zone_label

    @property
    def _map_btn(self):
        return self._breadcrumb_bar._map_btn

    @property
    def _entity_list(self):
        return self._entity_sidebar._entity_list

    @property
    def entity_list(self) -> QListWidget:
        """Public accessor for the entity list widget."""
        return self._entity_sidebar._entity_list

    # ── Layout ────────────────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()

        # Breadcrumb: top, full width
        self._breadcrumb_bar.setGeometry(0, 0, w, 32)

        # NPC panel: above nav buttons
        panel_w = min(600, int(w * 0.8))
        self._npc_panel.setGeometry((w - panel_w) // 2, h - 90, panel_w, 44)
        self._npc_panel.raise_()

        # Nav buttons: bottom row
        self._nav_overlay.reposition(w, h)


        # Status: bottom-left, above nav buttons
        self._status.adjustSize()
        self._status.move(8, h - self._status.height() - 40)

        # Breadcrumb always on top
        self._breadcrumb_bar.raise_()

    # ── Input ─────────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        key = event.key()
        directions = {
            Qt.Key_Up: (-1, 0), Qt.Key_W: (-1, 0),
            Qt.Key_Down: (1, 0), Qt.Key_S: (1, 0),
            Qt.Key_Left: (0, -1), Qt.Key_A: (0, -1),
            Qt.Key_Right: (0, 1), Qt.Key_D: (0, 1),
        }
        delta = directions.get(key)
        if delta:
            self.navigate_direction.emit(delta[0], delta[1])
        else:
            super().keyPressEvent(event)

    # ── Zone loading ──────────────────────────────────────────────

    def load_zone(self, scene_data: ZoneSceneData,
                  entities: list | None = None) -> None:
        self._crossfade_content()
        self._npc_panel.hide()
        self._scene_data = scene_data
        self._breadcrumb_bar._zone_label.setText(scene_data.zone_label)
        self._canvas.set_scene(scene_data)
        self._nav_overlay.set_arrows(scene_data.nav_arrows)
        self._nav_overlay.reposition(self.width(), self.height())
        # Build name->entity lookup
        entity_map: dict[str, Any] = {}
        if entities:
            for e in entities:
                entity_map[getattr(e, "name", "")] = e
        # Populate entity sidebar
        el = self._entity_sidebar._entity_list
        el.clear()
        for depth in sorted(scene_data.objects_by_depth.keys()):
            for obj in scene_data.objects_by_depth[depth]:
                colour = {"friendly": "#4ad97a", "hostile": "#d94a4a",
                          "neutral": "#d9c84a"}.get(obj.faction, "#888888")
                item = QListWidgetItem(f"{obj.name} ({obj.obj_type})")
                item.setForeground(QColor(colour))
                entity = entity_map.get(obj.name)
                item.setData(Qt.UserRole, entity if entity else obj.name)
                item.setData(Qt.UserRole + 1, obj.name)
                el.addItem(item)

    def load_simple_tile(self, label: str, note: str,
                         entities: list, info_filter=None,
                         background_image: str | None = None,
                         nav_arrows=None) -> None:
        """Show a tile without zones."""
        self._crossfade_content()
        self._npc_panel.hide()
        self._scene_data = None
        self._breadcrumb_bar._zone_label.setText(label)
        if background_image:
            from models.exploration.zone_scene_data import ZoneSceneData
            simple_scene = ZoneSceneData(
                zone_id="", zone_label=label, zone_description=note or "",
                objects_by_depth={1: [], 2: [], 3: []}, nav_arrows=[],
                background_image=background_image,
            )
            self._canvas.set_scene(simple_scene)
        else:
            self._canvas.set_scene(None)
        self._nav_overlay.set_arrows(nav_arrows or [])
        self._nav_overlay.reposition(self.width(), self.height())
        self._populate_entity_list(entities, info_filter)
        self._status.setText(note if note else "Click entities to interact")

    def highlight_entity(self, entity_name: str) -> None:
        self._canvas.highlight_entity(entity_name)

    # ── NPC panel ─────────────────────────────────────────────────

    @property
    def npc_panel(self) -> "NpcInteractionPanel":
        return self._npc_panel

    def show_npc_panel(self, entity_name: str, interactions: list[dict]) -> None:
        self._npc_panel.show_for_entity(entity_name, interactions)

    def hide_npc_panel(self) -> None:
        self._npc_panel.hide_panel()

    def show_info_toast(self, text: str, duration_ms: int = 4000) -> None:
        """Show a floating info card in the center of the view, auto-dismiss."""
        from PyQt5.QtCore import QTimer
        self._info_toast.setText(text)
        self._info_toast.adjustSize()
        # Center horizontally, upper third vertically
        w = self.width()
        tw = min(self._info_toast.sizeHint().width() + 32, int(w * 0.6))
        self._info_toast.setFixedWidth(tw)
        self._info_toast.adjustSize()
        x = (w - self._info_toast.width()) // 2
        y = self.height() // 4
        self._info_toast.move(x, y)
        self._info_toast.show()
        self._info_toast.raise_()
        # Auto-dismiss
        if self._info_toast_timer is not None:
            self._info_toast_timer.stop()
        self._info_toast_timer = QTimer(self)
        self._info_toast_timer.setSingleShot(True)
        self._info_toast_timer.timeout.connect(self._info_toast.hide)
        self._info_toast_timer.start(duration_ms)

    # ── Entity list helpers ───────────────────────────────────────

    def _populate_entity_list(self, entities: list, info_filter=None) -> None:
        el = self._entity_sidebar._entity_list

        # Build desired display items
        desired: list[tuple[str, str, str, object]] = []  # (name, text, colour, entity)
        for entity in entities:
            etype = getattr(entity, "entity_type", "")
            name = getattr(entity, "name", "?")
            colour = self._TYPE_COLORS.get(etype, "#888888")
            parts = [name]
            show_hp = (info_filter and info_filter.can_see_hp(name)) or etype == "player"
            if show_hp:
                hp = getattr(entity, "hp", None)
                max_hp = getattr(entity, "max_hp", None)
                if hp is not None and max_hp:
                    parts.append(f"{hp}/{max_hp} HP")
            if etype and etype != "player":
                parts.append(etype)
            desired.append((name, " — ".join(parts), colour, entity))

        # Fast-path: same entities — update text in-place (avoids flicker)
        new_names = tuple(d[0] for d in desired)
        if hasattr(self, "_last_entity_names") and self._last_entity_names == new_names:
            for i, (name, text, colour, entity) in enumerate(desired):
                if i < el.count():
                    item = el.item(i)
                    item.setText(text)
                    item.setData(Qt.UserRole, entity)
            self._last_entity_names = new_names
            return
        self._last_entity_names = new_names

        # Full rebuild
        el.clear()
        if not desired:
            placeholder = QListWidgetItem("(no one here)")
            placeholder.setFlags(Qt.NoItemFlags)
            placeholder.setForeground(QColor("#666"))
            el.addItem(placeholder)
            return
        for name, text, colour, entity in desired:
            item = QListWidgetItem(text)
            item.setForeground(QColor(colour))
            item.setData(Qt.UserRole, entity)
            item.setData(Qt.UserRole + 1, name)
            item.setFlags(item.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            el.addItem(item)

    def _on_list_entity_clicked(self, entity) -> None:
        if entity is not None:
            self.entity_clicked.emit(entity)

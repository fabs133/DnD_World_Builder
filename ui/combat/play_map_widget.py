"""Lightweight read-only map scene for the play session dialog.

Renders tiles from map.json data with terrain colors and entity tokens.
Reuses CombatTileItem for rendering. Includes fog of war — only tiles
near player entities are visible.
"""

from __future__ import annotations

import math

from PyQt5.QtCore import Qt, QTimer, QTimeLine, pyqtSignal
from PyQt5.QtWidgets import (
    QGraphicsScene, QGraphicsItem, QGraphicsRectItem,
    QGraphicsLineItem, QGraphicsTextItem, QGraphicsPathItem,
)
from PyQt5.QtGui import QBrush, QColor, QCursor, QPainterPath, QPen

from ui.combat.combat_tile_item import CombatTileItem
from ui.widgets.rich_tooltip import RichTooltipWidget
from models.entities.game_entity import GameEntity


def make_decorative(item):
    """Make a QGraphicsItem purely decorative — NEVER intercepts mouse events."""
    item.setAcceptedMouseButtons(Qt.NoButton)
    item.setAcceptHoverEvents(False)
    item.setFlag(QGraphicsItem.ItemIsSelectable, False)
    item.setFlag(QGraphicsItem.ItemIsMovable, False)
    return item


class RangeOutline:
    """Pulsing dashed border at the edge of a range on the combat map."""

    def __init__(self, scene: QGraphicsScene, tile_size: int):
        self._scene = scene
        self._tile_size = tile_size
        self._outline_item: QGraphicsPathItem | None = None
        self._pulse_timer: QTimeLine | None = None

    def show(self, reachable_positions: set[tuple[int, int]],
             tiles_lookup: dict, color: str = "#378ADD") -> None:
        """Draw a pulsing dashed border around the given set of reachable tiles."""
        self.clear()
        if not reachable_positions:
            return
        ts = self._tile_size
        path = QPainterPath()
        # Draw a rect outline on each border tile (tiles at the edge of the set)
        for (r, c) in reachable_positions:
            tile = tiles_lookup.get((r, c))
            if not tile or not tile.isVisible():
                continue
            # Only draw edges that face non-reachable tiles
            tx = tile.pos().x()
            ty = tile.pos().y()
            if (r - 1, c) not in reachable_positions:
                path.moveTo(tx, ty)
                path.lineTo(tx + ts, ty)  # top edge
            if (r + 1, c) not in reachable_positions:
                path.moveTo(tx, ty + ts)
                path.lineTo(tx + ts, ty + ts)  # bottom edge
            if (r, c - 1) not in reachable_positions:
                path.moveTo(tx, ty)
                path.lineTo(tx, ty + ts)  # left edge
            if (r, c + 1) not in reachable_positions:
                path.moveTo(tx + ts, ty)
                path.lineTo(tx + ts, ty + ts)  # right edge

        self._outline_item = make_decorative(QGraphicsPathItem(path))
        pen = QPen(QColor(color), 2.5, Qt.DashLine)
        pen.setDashPattern([6, 4])
        self._outline_item.setPen(pen)
        self._outline_item.setBrush(QBrush(Qt.NoBrush))
        self._outline_item.setZValue(5)
        self._scene.addItem(self._outline_item)

        # Pulse opacity 0.4 → 1.0 → 0.4 over 1.5s, looping
        self._pulse_timer = QTimeLine(1500)
        self._pulse_timer.setFrameRange(0, 100)
        self._pulse_timer.setLoopCount(0)

        def _pulse(frame):
            if self._outline_item:
                t = frame / 100.0
                opacity = 0.4 + 0.6 * abs(math.sin(t * math.pi))
                self._outline_item.setOpacity(opacity)

        self._pulse_timer.frameChanged.connect(_pulse)
        self._pulse_timer.start()

    def clear(self) -> None:
        if self._pulse_timer:
            self._pulse_timer.stop()
            self._pulse_timer = None
        if self._outline_item and self._outline_item.scene():
            self._outline_item.scene().removeItem(self._outline_item)
            self._outline_item = None


from core.constants import DEFAULT_VISION_RADIUS
from ui.theme.terrain_colors import TERRAIN_COLORS, DEFAULT_TERRAIN_COLOR, FOG_COLOR

VISION_RADIUS = DEFAULT_VISION_RADIUS


class PlayMapScene(QGraphicsScene):
    """Read-only map scene that renders tiles from map.json tile dicts.

    Entity tokens are updated each turn from live GameEntity positions.
    Fog of war hides tiles that are not near any living player entity.
    """

    tile_double_clicked = pyqtSignal(dict)  # Emits tile_dict for the clicked tile
    tile_clicked = pyqtSignal(int, int)    # Emits (row, col) on single click
    tile_hovered = pyqtSignal(int, int)    # Emits (row, col) on hover
    cursor_moved = pyqtSignal(float, float)  # Raw scene coords for multiplayer sharing
    draw_completed = pyqtSignal(list)        # [[x,y], ...] polyline points on release

    def __init__(self, tile_dicts: list[dict], tile_size: int = 36, parent=None):
        super().__init__(parent)
        self._tile_dicts = tile_dicts
        self._tile_size = tile_size
        self._fog_enabled = True
        self._tiles: dict[tuple[int, int], CombatTileItem] = {}
        self._revealed: set[tuple[int, int]] = set()
        self._overlay_items: list[QGraphicsRectItem] = []
        self._entity_positions: dict[tuple[int, int], "GameEntity"] = {}  # (row,col)->entity
        self._last_hovered: tuple[int, int] | None = None
        self._path_items: list = []
        self._tile_dict_by_pos: dict[tuple[int, int], dict] = {}
        # Multiplayer: remote cursors and draw strokes
        self._remote_cursors: dict[str, "QGraphicsItemGroup"] = {}
        self._cursor_timers: dict[str, QTimer] = {}
        self._draw_strokes: list["QGraphicsPathItem"] = []
        self._draw_mode = False
        self._draw_points: list[list[float]] = []
        self._draw_preview_item: "QGraphicsPathItem | None" = None
        self._MAX_DRAW_POINTS = 200
        self._multiplayer_active = False  # Set True by connect_session_manager
        for td in tile_dicts:
            pos = td.get("position", [0, 0])
            self._tile_dict_by_pos[(pos[0], pos[1])] = td

        # Rich tooltip support
        self._tooltip = RichTooltipWidget()
        self._tooltip_timer = QTimer()
        self._tooltip_timer.setSingleShot(True)
        self._tooltip_timer.setInterval(400)
        self._tooltip_timer.timeout.connect(self._show_pending_tooltip)
        self._pending_tooltip_pos = None
        self._info_filter = None

        self._build_grid()

    def _build_grid(self) -> None:
        self.clear()
        self._tiles.clear()

        for td in self._tile_dicts:
            pos = td.get("position", [0, 0])
            row, col = pos[0], pos[1]
            terrain = td.get("terrain", "GRASS")
            tags = td.get("tags", [])
            elevation = td.get("elevation", 0)

            item = CombatTileItem(
                col=col, row=row,
                tile_size=self._tile_size,
                elevation=elevation,
                terrain_type=terrain,
                tags=tags,
            )

            # Apply terrain/overlay color
            overlay_hex = td.get("overlay_color")
            if overlay_hex:
                item.set_overlay(QColor(overlay_hex), opacity=0.5)
            else:
                terrain_color = TERRAIN_COLORS.get(terrain.upper(), DEFAULT_TERRAIN_COLOR)
                item.set_overlay(terrain_color, opacity=0.35)

            # Mark tiles with zone detail available
            if td.get("zones"):
                item._has_zones = True

            # Start hidden (fog of war)
            item.setVisible(False)

            self.addItem(item)
            self._tiles[(row, col)] = item

        # Set scene rect explicitly from all tile positions (even hidden ones)
        if self._tiles:
            min_r = min(r for r, c in self._tiles)
            max_r = max(r for r, c in self._tiles)
            min_c = min(c for r, c in self._tiles)
            max_c = max(c for r, c in self._tiles)
            ts = self._tile_size
            from PyQt5.QtCore import QRectF
            self.setSceneRect(QRectF(
                min_c * ts - ts, min_r * ts - ts,
                (max_c - min_c + 2) * ts,
                (max_r - min_r + 2) * ts,
            ))

        self.update()

    def reset(self, tile_dicts: list[dict], tile_size: int | None = None) -> None:
        """Reconfigure the grid for a new combat without full reconstruction.

        Tiles at matching ``(row, col)`` are updated in-place.
        Tiles no longer needed are removed.  New positions get fresh items.
        """
        if tile_size is not None:
            self._tile_size = tile_size
        self._tile_dicts = tile_dicts
        self._tile_dict_by_pos.clear()
        for td in tile_dicts:
            pos = td.get("position", [0, 0])
            self._tile_dict_by_pos[(pos[0], pos[1])] = td

        new_positions = set(self._tile_dict_by_pos.keys())
        old_positions = set(self._tiles.keys())

        # Remove tiles no longer in the grid
        for pos in old_positions - new_positions:
            item = self._tiles.pop(pos)
            self.removeItem(item)

        # Update existing or create new tiles
        for td in tile_dicts:
            pos = td.get("position", [0, 0])
            row, col = pos[0], pos[1]
            terrain = td.get("terrain", "GRASS")
            tags = td.get("tags", [])
            elevation = td.get("elevation", 0)

            if (row, col) in self._tiles:
                item = self._tiles[(row, col)]
                item._terrain_type = terrain
                item._tags = tags
                item.set_elevation(elevation)
                item.clear_token()
                item._has_zones = bool(td.get("zones"))
            else:
                item = CombatTileItem(
                    col=col, row=row,
                    tile_size=self._tile_size,
                    elevation=elevation, terrain_type=terrain, tags=tags,
                )
                self.addItem(item)
                self._tiles[(row, col)] = item

            # Apply terrain color
            overlay_hex = td.get("overlay_color")
            if overlay_hex:
                item.set_overlay(QColor(overlay_hex), opacity=0.5)
            else:
                terrain_color = TERRAIN_COLORS.get(terrain.upper(), DEFAULT_TERRAIN_COLOR)
                item.set_overlay(terrain_color, opacity=0.35)

            item.setVisible(False)  # fog starts hidden

        # Clear overlays, paths, and state from previous combat
        self.clear_all_overlays()
        self.clear_path_preview()
        self._revealed.clear()
        self._entity_positions.clear()
        self._last_hovered = None

        # Recompute scene rect
        if self._tiles:
            min_r = min(r for r, c in self._tiles)
            max_r = max(r for r, c in self._tiles)
            min_c = min(c for r, c in self._tiles)
            max_c = max(c for r, c in self._tiles)
            ts = self._tile_size
            from PyQt5.QtCore import QRectF
            self.setSceneRect(QRectF(
                min_c * ts - ts, min_r * ts - ts,
                (max_c - min_c + 2) * ts,
                (max_r - min_r + 2) * ts,
            ))
        self.update()

    def set_fog_enabled(self, enabled: bool) -> None:
        """Toggle fog of war. When disabled (DM), all tiles are visible."""
        self._fog_enabled = enabled
        if not enabled:
            for item in self._tiles.values():
                item.setVisible(True)
                item.setOpacity(1.0)

    def update_entities(self, entities: list[GameEntity],
                        current_name: str | None = None,
                        vision_entities: list | None = None) -> None:
        """Refresh entity tokens and fog of war from live GameEntity positions.

        Args:
            vision_entities: If provided, use these entities for fog calculation
                instead of all player entities. Pass an empty list to disable fog.
        """
        if self._fog_enabled:
            # Determine fog vision sources
            if vision_entities is not None:
                fog_sources = vision_entities
            else:
                fog_sources = [e for e in entities
                               if getattr(e, "entity_type", "") == "player"]

            # Compute visible tiles from vision source positions
            player_positions = []
            for entity in fog_sources:
                pos = getattr(entity, "position", None)
                if not pos:
                    continue
                hp = getattr(entity, "hp", 0)
                if hp <= 0:
                    continue
                player_positions.append((pos[0], pos[1]))

            visible_now: set[tuple[int, int]] = set()
            for pr, pc in player_positions:
                for dr in range(-VISION_RADIUS, VISION_RADIUS + 1):
                    for dc in range(-VISION_RADIUS, VISION_RADIUS + 1):
                        if abs(dr) + abs(dc) <= VISION_RADIUS:
                            visible_now.add((pr + dr, pc + dc))

            self._revealed |= visible_now

            # Update tile visibility:
            #   discovered = solid (0.9), current vision = subtle highlight (0.6)
            for pos, item in self._tiles.items():
                if pos in self._revealed:
                    item.setVisible(True)
                    item.setOpacity(0.9)
                else:
                    item.setVisible(False)
            # Brighten tiles in current vision range
            for pos in visible_now:
                item = self._tiles.get(pos)
                if item:
                    item.setVisible(True)
                    item.setOpacity(1.0)
        else:
            # No fog — all tiles visible
            visible_now = set(self._tiles.keys())

        # Clear all tokens and entity position tracking
        for item in self._tiles.values():
            item.clear_token()
        self._entity_positions.clear()

        # Place tokens only on currently visible tiles
        for entity in entities:
            pos = getattr(entity, "position", None)
            if not pos:
                continue
            hp = getattr(entity, "hp", 0)
            if hp <= 0:
                continue

            row, col = pos[0], pos[1]
            if (row, col) not in visible_now:
                continue

            tile = self._tiles.get((row, col))
            if tile:
                is_current = (entity.name == current_name) if current_name else False
                from ui.animations.portrait_resolver import resolve_portrait
                from pathlib import Path
                base = str(Path(__file__).resolve().parent.parent.parent)
                portrait = resolve_portrait(entity, base_dir=base)
                tile.set_token(
                    entity.name,
                    getattr(entity, "entity_type", "neutral"),
                    is_current_turn=is_current,
                    portrait_path=portrait,
                )
                tile.set_conditions(getattr(entity, "conditions", []))
                self._entity_positions[(row, col)] = entity

    def entity_at(self, row: int, col: int):
        """Return the GameEntity at the given grid position, or None."""
        return self._entity_positions.get((row, col))

    def set_info_filter(self, info_filter):
        """Set the info filter used for role-aware tooltip content."""
        self._info_filter = info_filter

    # ------------------------------------------------------------------
    # Current position highlight
    # ------------------------------------------------------------------

    _current_highlight: QGraphicsRectItem | None = None

    def highlight_current_tile(self, row: int, col: int) -> None:
        """Draw a pulsing border around the tile the player is currently on."""
        # Remove old highlight
        if self._current_highlight and self._current_highlight.scene():
            self.removeItem(self._current_highlight)
            self._current_highlight = None

        tile = self._tiles.get((row, col))
        if not tile:
            return

        ts = self._tile_size
        rect = QGraphicsRectItem(col * ts, row * ts, ts, ts)
        rect.setPen(QPen(QColor(255, 220, 60, 200), 3))
        rect.setBrush(QBrush(QColor(255, 220, 60, 40)))
        rect.setZValue(100)
        make_decorative(rect)
        self.addItem(rect)
        self._current_highlight = rect

    # ------------------------------------------------------------------
    # Tile interaction
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        """Handle tile clicks and draw mode capture."""
        # Draw mode intercepts left-click
        if self._draw_mode and event.button() == Qt.LeftButton:
            pos = event.scenePos()
            self._draw_points = [[pos.x(), pos.y()]]
            return

        views = self.views()
        if views:
            item = self.itemAt(event.scenePos(), views[0].transform())
            if isinstance(item, CombatTileItem) and item.isVisible():
                item.pulse_select()
                self.tile_clicked.emit(item.row, item.col)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """Emit tile_double_clicked when a visible tile is double-clicked."""
        views = self.views()
        if not views:
            super().mouseDoubleClickEvent(event)
            return
        item = self.itemAt(event.scenePos(), views[0].transform())
        if isinstance(item, CombatTileItem) and item.isVisible():
            pos = (item.row, item.col)
            td = self._tile_dict_by_pos.get(pos)
            if td:
                self.tile_double_clicked.emit(td)
                return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Emit tile_hovered when cursor moves over a new tile.

        Also emits ``cursor_moved`` with raw scene coordinates for
        multiplayer cursor sharing, and captures draw points when
        draw mode is active.
        """
        scene_pos = event.scenePos()
        if self._multiplayer_active:
            self.cursor_moved.emit(scene_pos.x(), scene_pos.y())

        # Draw mode: accumulate points
        if self._draw_mode and self._draw_points is not None:
            if len(self._draw_points) < self._MAX_DRAW_POINTS:
                self._draw_points.append([scene_pos.x(), scene_pos.y()])
                self._update_draw_preview()
            else:
                # Max length reached — auto-finalize
                self._finalize_draw()

        views = self.views()
        if views:
            item = self.itemAt(scene_pos, views[0].transform())
            if isinstance(item, CombatTileItem) and item.isVisible():
                pos = (item.row, item.col)
                if pos != self._last_hovered:
                    self._last_hovered = pos
                    self.tile_hovered.emit(item.row, item.col)
                    # Restart tooltip timer for new tile
                    self._tooltip_timer.stop()
                    self._tooltip.hide_tooltip()
                    self._pending_tooltip_pos = pos
                    self._tooltip_timer.start()
            else:
                self._last_hovered = None
                self._tooltip_timer.stop()
                self._tooltip.hide_tooltip()
        super().mouseMoveEvent(event)

    # ------------------------------------------------------------------
    # Tooltip
    # ------------------------------------------------------------------

    def _show_pending_tooltip(self):
        pos = self._pending_tooltip_pos
        if pos is None:
            return
        td = self._tile_dict_by_pos.get(pos)
        entity = self._entity_positions.get(pos)
        role = "dm"
        if self._info_filter:
            role = getattr(self._info_filter, '_role', 'dm')
            if hasattr(role, 'value'):
                role = role.value.lower()

        if entity:
            self._tooltip.set_entity_content(
                name=getattr(entity, "name", "?"),
                entity_type=str(getattr(entity, "entity_type", "")),
                hp=getattr(entity, "hp", 0),
                max_hp=getattr(entity, "max_hp", 0),
                ac=getattr(entity, "armor_class", 10),
                conditions=getattr(entity, "conditions", []),
                role=role,
            )
        elif td:
            terrain = td.get("terrain", "unknown")
            elevation = td.get("elevation", 0)
            tags = td.get("tags", [])
            entities_on_tile = td.get("entities", [])
            entity_dicts = [
                {"name": getattr(e, "name", str(e))} if not isinstance(e, dict) else e
                for e in entities_on_tile
            ]
            self._tooltip.set_tile_content(terrain, elevation, tags, entity_dicts, role)
        else:
            return

        self._tooltip.show_at(QCursor.pos())

    # ------------------------------------------------------------------
    # Overlay adapter — CombatOverlay compatibility
    # ------------------------------------------------------------------

    def apply_overlay_to_tiles(self, tile_positions: list,
                               color: QColor) -> None:
        """Apply outline-only borders to specified tile positions.

        Uses outlines (no fill) so clicks pass through to the tiles beneath.
        """
        for pos in tile_positions:
            key = (pos[0], pos[1]) if isinstance(pos, (list, tuple)) else pos
            tile = self._tiles.get(key)
            if not tile or not tile.isVisible():
                continue
            rect = make_decorative(QGraphicsRectItem(tile.rect()))
            rect.setPos(tile.pos())
            rect.setBrush(QBrush(Qt.NoBrush))
            rect.setPen(QPen(color, 2.0))
            rect.setZValue(5)
            self.addItem(rect)
            self._overlay_items.append(rect)

    def clear_all_overlays(self) -> None:
        """Remove all overlay items from scene."""
        for item in self._overlay_items:
            self.removeItem(item)
        self._overlay_items.clear()

    def get_tile_scene_center(self, row: int, col: int):
        """Return the scene-space center of the tile at (row, col), or None."""
        tile = self._tiles.get((row, col))
        if tile:
            from PyQt5.QtCore import QPointF
            return QPointF(tile.pos().x() + self._tile_size / 2,
                           tile.pos().y() + self._tile_size / 2)
        return None

    # ------------------------------------------------------------------
    # Path preview
    # ------------------------------------------------------------------

    def show_path_preview(self, path: list[tuple], in_range: bool = True) -> None:
        """Draw A* path as line segments through tile centers with distance label."""
        self.clear_path_preview()
        if not path or len(path) < 2:
            return
        ts = self._tile_size
        color = QColor("#378ADD") if in_range else QColor("#888780")
        pen = QPen(color, 2.5)
        pen.setCapStyle(Qt.RoundCap)

        for i in range(len(path) - 1):
            r1, c1 = path[i]
            r2, c2 = path[i + 1]
            t1 = self._tiles.get((r1, c1))
            t2 = self._tiles.get((r2, c2))
            if not t1 or not t2:
                continue
            x1 = t1.pos().x() + ts / 2
            y1 = t1.pos().y() + ts / 2
            x2 = t2.pos().x() + ts / 2
            y2 = t2.pos().y() + ts / 2
            line = make_decorative(QGraphicsLineItem(x1, y1, x2, y2))
            line.setPen(pen)
            line.setZValue(6)
            self.addItem(line)
            self._path_items.append(line)

        # Distance label at end
        last_r, last_c = path[-1]
        last_tile = self._tiles.get((last_r, last_c))
        if last_tile:
            dist_ft = (len(path) - 1) * 5
            label = make_decorative(QGraphicsTextItem(f"{dist_ft} ft"))
            label.setDefaultTextColor(color)
            label.setPos(last_tile.pos().x() + ts + 2,
                         last_tile.pos().y() - 4)
            label.setZValue(7)
            self.addItem(label)
            self._path_items.append(label)

    def clear_path_preview(self) -> None:
        """Remove path preview items."""
        for item in self._path_items:
            self.removeItem(item)
        self._path_items.clear()

    # ------------------------------------------------------------------
    # Multiplayer: Remote cursors
    # ------------------------------------------------------------------

    def update_remote_cursor(
        self, player_id: str, player_name: str,
        x: float, y: float, color: str,
    ) -> None:
        """Show or move another player's cursor ghost on the map."""
        from PyQt5.QtGui import QColor, QBrush, QPen, QFont

        if player_id not in self._remote_cursors:
            # Create cursor group: colored circle + name label
            group = self.createItemGroup([])

            circle = QGraphicsEllipseItem(-6, -6, 12, 12)
            circle.setBrush(QBrush(QColor(color)))
            circle.setPen(QPen(QColor(color).darker(130), 1.5))
            make_decorative(circle)
            group.addToGroup(circle)

            label = QGraphicsTextItem(player_name)
            label.setDefaultTextColor(QColor(color))
            label.setFont(QFont("Segoe UI", 8, QFont.Bold))
            label.setPos(8, -8)
            make_decorative(label)
            group.addToGroup(label)

            make_decorative(group)
            group.setZValue(15)
            group.setOpacity(0.85)
            self._remote_cursors[player_id] = group

        group = self._remote_cursors[player_id]
        group.setPos(x, y)
        group.setOpacity(0.85)
        group.show()

        # Reset fade-out timer (5s idle → fade)
        if player_id in self._cursor_timers:
            self._cursor_timers[player_id].stop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda pid=player_id: self._fade_cursor(pid))
        timer.start(5000)
        self._cursor_timers[player_id] = timer

    def _fade_cursor(self, player_id: str) -> None:
        """Fade out a cursor that hasn't updated in 5 seconds."""
        group = self._remote_cursors.get(player_id)
        if group:
            group.setOpacity(0.2)

    def remove_remote_cursor(self, player_id: str) -> None:
        """Remove a disconnected player's cursor."""
        group = self._remote_cursors.pop(player_id, None)
        if group:
            self.destroyItemGroup(group)
        timer = self._cursor_timers.pop(player_id, None)
        if timer:
            timer.stop()

    # ------------------------------------------------------------------
    # Multiplayer: Draw mode
    # ------------------------------------------------------------------

    def set_draw_mode(self, active: bool) -> None:
        """Enable or disable draw mode."""
        self._draw_mode = active
        if not active and self._draw_points:
            self._finalize_draw()
        if not active:
            self._draw_points = []

    def mouseReleaseEvent(self, event) -> None:
        """Finalize draw stroke in draw mode; normal behavior otherwise."""
        if self._draw_mode and event.button() == Qt.LeftButton:
            if len(self._draw_points) >= 2:
                self._finalize_draw()
            else:
                self._draw_points = []
                self._clear_draw_preview()
            return
        super().mouseReleaseEvent(event)

    def _finalize_draw(self) -> None:
        """Emit the completed draw stroke and show it locally."""
        self._clear_draw_preview()
        if len(self._draw_points) >= 2:
            # Show locally immediately
            self.show_draw_stroke("local", list(self._draw_points), "#ffffff")
            self.draw_completed.emit(list(self._draw_points))
        self._draw_points = []

    def _update_draw_preview(self) -> None:
        """Render a dashed preview of the stroke being drawn."""
        from PyQt5.QtGui import QPainterPath, QPen, QColor

        self._clear_draw_preview()
        if len(self._draw_points) < 2:
            return

        path = QPainterPath()
        path.moveTo(self._draw_points[0][0], self._draw_points[0][1])
        for pt in self._draw_points[1:]:
            path.lineTo(pt[0], pt[1])

        item = QGraphicsPathItem(path)
        pen = QPen(QColor("#ffffff"), 2, Qt.DashLine)
        item.setPen(pen)
        make_decorative(item)
        item.setZValue(14)
        item.setOpacity(0.6)
        self.addItem(item)
        self._draw_preview_item = item

    def _clear_draw_preview(self) -> None:
        if self._draw_preview_item:
            self.removeItem(self._draw_preview_item)
            self._draw_preview_item = None

    # ------------------------------------------------------------------
    # Multiplayer: Received draw strokes
    # ------------------------------------------------------------------

    def show_draw_stroke(
        self, player_id: str, points: list, color: str,
    ) -> None:
        """Render a draw stroke from another player, auto-fading after 12s."""
        from PyQt5.QtGui import QPainterPath, QPen, QColor

        if len(points) < 2:
            return

        path = QPainterPath()
        path.moveTo(points[0][0], points[0][1])
        for pt in points[1:]:
            path.lineTo(pt[0], pt[1])

        item = QGraphicsPathItem(path)
        pen = QPen(QColor(color), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        item.setPen(pen)
        make_decorative(item)
        item.setZValue(14)
        self.addItem(item)
        self._draw_strokes.append(item)

        # Auto-fade: start fading at 12s, fully removed at 15s
        def start_fade():
            self._fade_stroke(item)
        QTimer.singleShot(12000, start_fade)

    def _fade_stroke(self, item: "QGraphicsPathItem") -> None:
        """Gradually fade a stroke over 3 seconds, then remove it."""
        steps = 10
        interval = 300  # 3s / 10 steps
        current_step = [0]

        def tick():
            current_step[0] += 1
            if current_step[0] >= steps:
                if item in self._draw_strokes:
                    self._draw_strokes.remove(item)
                self.removeItem(item)
                return
            item.setOpacity(1.0 - current_step[0] / steps)

        timer = QTimer()
        timer.timeout.connect(tick)
        timer.start(interval)
        # Store timer ref on the item to prevent GC
        item._fade_timer = timer

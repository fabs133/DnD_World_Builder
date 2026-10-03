"""Fog-of-war overlay for the player view (one mask item per non-visible tile)."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor, QPen, QPolygonF
from PyQt5.QtWidgets import QGraphicsPolygonItem, QGraphicsScene

from core.engine.vision import FogOfWar, Visibility, visible_positions, vision_range_tiles
from ui.entity_tokens import TOKEN_KIND_KEY, TOKEN_POS_KEY, is_dead

try:  # sip ships with PyQt5; guard so a layout change never breaks the import
    from PyQt5 import sip
except ImportError:  # pragma: no cover
    sip = None

FOG_Z = 500  # above tiles (0), below entity tokens (1000)
HIDDEN_COLOR = QColor(17, 17, 17, 255)
EXPLORED_COLOR = QColor(17, 17, 17, 150)


def _alive(item) -> bool:
    return item is not None and not (sip is not None and sip.isdeleted(item))


def _is_player(entity) -> bool:
    raw = getattr(entity, "entity_type", "")
    return str(getattr(raw, "value", raw)).strip().lower() == "player"


def _tile_polygon(tile) -> QPolygonF:
    """Scene-space outline of a tile item (hex polygon, or the square's rectangle)."""
    if hasattr(tile, "polygon"):
        return tile.mapToScene(tile.polygon())
    return QPolygonF(tile.mapToScene(tile.rect()))


class FogOfWarLayer:
    """Owns a :class:`FogOfWar` and draws it over the tiles of a scene."""

    def __init__(self, scene: QGraphicsScene, grid_type: Callable[[], str] | str = "square"):
        self._scene = scene
        self._grid_type = grid_type if callable(grid_type) else (lambda: grid_type)
        self.fog = FogOfWar()
        self.enabled = False
        self._items: list = []
        self._has_viewers = False

    @property
    def overlays(self) -> list:
        return [i for i in self._items if _alive(i) and i.scene() is not None]

    def has_viewers(self) -> bool:
        return self._has_viewers

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        self.refresh()

    def reset(self) -> None:
        """Forget explored tiles (call after the map changes)."""
        self.fog.reset()

    def clear(self) -> None:
        for item in self._items:
            if _alive(item) and item.scene() is not None:
                item.scene().removeItem(item)
        self._items = []

    def _tiles(self) -> list:
        return [i for i in self._scene.items() if hasattr(i, "tile_data")]

    def _tokens(self) -> list:
        return [
            i for i in self._scene.items() if i.data(TOKEN_POS_KEY) is not None and _alive(i)
        ]

    def update(self, viewers=None) -> None:
        """Recompute visibility. ``viewers`` is a list of ``(position, range)`` pairs;
        by default the living player entities on the scene's tiles."""
        self.refresh(viewers)

    def refresh(self, viewers=None) -> None:
        self.clear()
        tiles = self._tiles()
        if not self.enabled:
            for token in self._tokens():
                token.setVisible(True)
            return

        by_pos = {t.tile_data.position: t.tile_data for t in tiles}
        if viewers is None:
            viewers = []
            for td in by_pos.values():
                for ent in getattr(td, "entities", None) or []:
                    if _is_player(ent) and not is_dead(ent):
                        viewers.append((td.position, vision_range_tiles(ent)))
        self._has_viewers = bool(viewers)

        manager = SimpleNamespace(tiles=by_pos, tile_type=self._grid_type())
        self.fog.update(visible_positions(viewers, manager))

        for tile in tiles:
            state = self.fog.state(tile.tile_data.position)
            if state is Visibility.VISIBLE:
                continue
            color = HIDDEN_COLOR if state is Visibility.HIDDEN else EXPLORED_COLOR
            self._add_overlay(_tile_polygon(tile), color)

        for token in self._tokens():
            hide = (
                token.data(TOKEN_KIND_KEY) != "player"
                and self.fog.state(token.data(TOKEN_POS_KEY)) is not Visibility.VISIBLE
            )
            token.setVisible(not hide)

    def _add_overlay(self, polygon: QPolygonF, color: QColor) -> None:
        item = QGraphicsPolygonItem(polygon)
        item.setBrush(QBrush(color))
        item.setPen(QPen(Qt.NoPen))
        item.setZValue(FOG_Z)
        item.setAcceptedMouseButtons(Qt.NoButton)
        item.setAcceptHoverEvents(False)
        self._scene.addItem(item)
        self._items.append(item)


__all__ = ["FogOfWarLayer", "FOG_Z"]

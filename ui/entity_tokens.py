"""Entity tokens drawn on the map (one circle per entity, inside its tile)."""

from __future__ import annotations

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPen
from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsScene, QGraphicsSimpleTextItem

try:  # sip ships with PyQt5; guard so a layout change never breaks the import
    from PyQt5 import sip
except ImportError:  # pragma: no cover
    sip = None

TOKEN_Z = 1000
MAX_TOKENS_PER_TILE = 4
TOKEN_COLORS = {
    "player": "#3A7BD5",
    "enemy": "#D64545",
    "npc": "#3FA55B",
    "other": "#E0A030",
}
DEAD_COLOR = "#808080"


def entity_kind(entity) -> str:
    """Normalise ``entity.entity_type`` (enum or string) to player/enemy/npc/other."""
    raw = getattr(entity, "entity_type", "")
    raw = getattr(raw, "value", raw)
    kind = str(raw).strip().lower()
    return kind if kind in ("player", "enemy", "npc") else "other"


def is_dead(entity) -> bool:
    return getattr(entity, "hp", 1) <= 0


def token_color(entity) -> str:
    if is_dead(entity):
        return DEAD_COLOR
    return TOKEN_COLORS[entity_kind(entity)]


def token_label(entity) -> str:
    name = str(getattr(entity, "name", "") or "?")
    return name[0].upper()


def token_tooltip(entity) -> str:
    raw = getattr(entity, "entity_type", "")
    kind = getattr(raw, "value", raw)
    hp = getattr(entity, "hp", "?")
    max_hp = getattr(entity, "max_hp", "?")
    return f"{entity.name} ({kind}) HP {hp}/{max_hp}"


def token_slots(count: int, cell: float) -> list[tuple[float, float, float]]:
    """Return ``(dx, dy, diameter)`` offsets from the tile centre for ``count`` tokens.

    One token is centred and large; 2-4 tokens use a 2x2 arrangement of smaller circles.
    """
    count = min(count, MAX_TOKENS_PER_TILE)
    if count <= 0:
        return []
    if count == 1:
        return [(0.0, 0.0, cell * 0.7)]
    d = cell * 0.4
    off = cell * 0.22
    quad = [(-off, -off), (off, -off), (-off, off), (off, off)]
    return [(x, y, d) for x, y in quad[:count]]


def _alive(item) -> bool:
    return item is not None and not (sip is not None and sip.isdeleted(item))


class EntityTokenLayer:
    """Draws entity tokens on a scene from the tiles' ``TileData.entities``."""

    def __init__(self, scene: QGraphicsScene):
        self._scene = scene
        self._items: list = []

    @property
    def tokens(self) -> list:
        return [i for i in self._items if _alive(i) and isinstance(i, QGraphicsEllipseItem)]

    def clear(self) -> None:
        for item in self._items:
            if _alive(item) and item.scene() is not None:
                item.scene().removeItem(item)
        self._items = []

    def refresh(self) -> None:
        self.clear()
        for tile in [i for i in self._scene.items() if hasattr(i, "tile_data")]:
            td = tile.tile_data
            entities = list(getattr(td, "entities", None) or [])
            if not entities:
                continue
            rect = tile.sceneBoundingRect()
            center = rect.center()
            cell = min(rect.width(), rect.height())
            for ent, (dx, dy, d) in zip(entities, token_slots(len(entities), cell)):
                self._add_token(ent, QPointF(center.x() + dx, center.y() + dy), d)

    def _add_token(self, entity, center: QPointF, diameter: float) -> None:
        circle = QGraphicsEllipseItem(QRectF(-diameter / 2, -diameter / 2, diameter, diameter))
        circle.setPos(center)
        circle.setBrush(QBrush(QColor(token_color(entity))))
        circle.setPen(QPen(QColor("#202020"), 1.5))
        circle.setZValue(TOKEN_Z)
        circle.setAcceptedMouseButtons(Qt.NoButton)
        circle.setToolTip(token_tooltip(entity))

        label = QGraphicsSimpleTextItem(token_label(entity), circle)
        font = QFont()
        font.setBold(True)
        font.setPixelSize(max(6, int(diameter * 0.55)))
        label.setFont(font)
        label.setBrush(QBrush(QColor("white")))
        label.setAcceptedMouseButtons(Qt.NoButton)
        br = label.boundingRect()
        label.setPos(-br.width() / 2, -br.height() / 2)

        self._scene.addItem(circle)
        self._items.append(circle)

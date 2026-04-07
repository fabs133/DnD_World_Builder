"""Fog of war overlay for the map scene.

Draws semi-transparent rectangles over hidden and revealed tiles.
Visible tiles receive no overlay.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QGraphicsRectItem
from PyQt5.QtGui import QColor, QBrush, QPen
from PyQt5.QtCore import Qt

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QGraphicsScene
    from core.engine.fog_state import FogOfWarState


# Overlay colours
_HIDDEN_COLOR = QColor(0, 0, 0, 230)     # near-black
_REVEALED_COLOR = QColor(0, 0, 0, 120)   # semi-dark
_Z_VALUE = 100  # above tiles, below UI elements


class FogOverlay:
    """Manages fog-of-war overlay items on a QGraphicsScene."""

    def __init__(self, scene: "QGraphicsScene", tile_size: int = 50):
        self._scene = scene
        self._tile_size = tile_size
        self._items: list[QGraphicsRectItem] = []

    def update(
        self,
        fog_state: "FogOfWarState",
        world_width: int,
        world_height: int,
    ) -> None:
        """Redraw the overlay based on current fog state.

        :param fog_state: The current :class:`FogOfWarState`.
        :param world_width: Grid width in tiles.
        :param world_height: Grid height in tiles.
        """
        self.clear()
        for x in range(world_width):
            for y in range(world_height):
                state = fog_state.get_tile_state((x, y))
                if state == "hidden":
                    self._add_rect(x, y, _HIDDEN_COLOR)
                elif state == "revealed":
                    self._add_rect(x, y, _REVEALED_COLOR)
                # "visible" → no overlay

    def clear(self) -> None:
        """Remove all overlay items from the scene."""
        for item in self._items:
            self._scene.removeItem(item)
        self._items.clear()

    @property
    def is_visible(self) -> bool:
        """True if the overlay is currently showing items."""
        return len(self._items) > 0

    def _add_rect(self, x: int, y: int, color: QColor) -> None:
        ts = self._tile_size
        rect = QGraphicsRectItem(y * ts, x * ts, ts, ts)
        rect.setBrush(QBrush(color))
        rect.setPen(QPen(Qt.NoPen))
        rect.setZValue(_Z_VALUE)
        self._scene.addItem(rect)
        self._items.append(rect)

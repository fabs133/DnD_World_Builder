"""Visual path overlay for the distance measurement tool.

Draws highlighted tiles along a measured path on the QGraphicsScene.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
from PyQt5.QtGui import QBrush, QColor, QPen, QFont
from PyQt5.QtCore import QRectF


class MeasureOverlay:
    """Manages path highlight items on a QGraphicsScene.

    Call :meth:`show_path` to draw highlighted tiles for a measured path,
    and :meth:`clear` to remove them.

    :param scene: The scene to draw on.
    :param tile_size: Pixel size of one tile (used for positioning).
    """

    PATH_COLOR = QColor(100, 200, 255, 100)
    PATH_BORDER = QColor(100, 200, 255, 200)
    LABEL_COLOR = QColor(255, 255, 255)

    def __init__(self, scene, tile_size: int = 50):
        self._scene = scene
        self._tile_size = tile_size
        self._items: list = []

    def show_path(
        self,
        path: list[tuple[int, int]],
        cost_feet: int,
        tile_size: int | None = None,
    ) -> None:
        """Draw highlighted rectangles for each tile in the path.

        :param path: List of (row, col) coordinates.
        :param cost_feet: Total cost to display on the label.
        :param tile_size: Override tile size for this call.
        """
        self.clear()
        size = tile_size or self._tile_size

        for row, col in path:
            rect = QGraphicsRectItem(
                QRectF(col * size, row * size, size, size)
            )
            rect.setBrush(QBrush(self.PATH_COLOR))
            rect.setPen(QPen(self.PATH_BORDER, 2))
            rect.setZValue(100)
            self._scene.addItem(rect)
            self._items.append(rect)

        # Cost label at the end of the path
        if path:
            end_row, end_col = path[-1]
            label = QGraphicsTextItem(f"{cost_feet}ft")
            label.setDefaultTextColor(self.LABEL_COLOR)
            label.setFont(QFont("Arial", 10, QFont.Bold))
            label.setPos(end_col * size + 2, end_row * size + 2)
            label.setZValue(101)
            self._scene.addItem(label)
            self._items.append(label)

    def clear(self) -> None:
        """Remove all overlay items from the scene."""
        for item in self._items:
            self._scene.removeItem(item)
        self._items.clear()

    @property
    def is_visible(self) -> bool:
        """Whether any overlay items are currently displayed."""
        return len(self._items) > 0

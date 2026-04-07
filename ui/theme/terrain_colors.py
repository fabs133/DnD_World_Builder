"""Shared terrain colour palette used by play-map and combat-tile rendering."""

from PyQt5.QtGui import QColor


# Terrain-type → base colour (used as overlay on play map tiles)
TERRAIN_COLORS: dict[str, QColor] = {
    "GRASS":    QColor(100, 140, 75),
    "WATER":    QColor(55, 95, 170),
    "MOUNTAIN": QColor(140, 130, 120),
    "FLOOR":    QColor(150, 140, 125),
    "WALL":     QColor(55, 50, 45),
    "CUSTOM":   QColor(130, 130, 130),
    "SAND":     QColor(190, 175, 130),
    "SWAMP":    QColor(75, 100, 65),
}

DEFAULT_TERRAIN_COLOR = QColor(100, 95, 85)
"""Fallback when terrain type is not in :data:`TERRAIN_COLORS`."""

FOG_COLOR = QColor(20, 20, 25)
"""Overlay colour for fog-of-war hidden tiles."""

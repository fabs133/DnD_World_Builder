"""Theme-aware SVG icon provider.

Loads monochrome SVG icons from ``assets/icons/ui/`` and tints them to
match the current theme's accent or text color.  Returns :class:`QIcon`
instances suitable for ``QPushButton.setIcon()``, ``QAction``, etc.
"""

from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtCore import Qt, QSize

from core import theme_palette as tp

_ICON_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons" / "ui"


@lru_cache(maxsize=64)
def _renderer(name: str):
    """Return a cached QSvgRenderer for the named icon, or None."""
    path = _ICON_DIR / f"{name}.svg"
    if not path.exists():
        return None
    try:
        from PyQt5.QtSvg import QSvgRenderer
        r = QSvgRenderer(str(path))
        return r if r.isValid() else None
    except Exception:
        return None


def themed_icon(name: str, color: str = "", size: int = 24) -> QIcon:
    """Return a QIcon tinted to the given or current accent color.

    :param name: Icon filename stem (e.g. ``"sword"`` for ``sword.svg``).
    :param color: Hex color override.  Defaults to ``accent_primary``.
    :param size: Pixel size for the rendered pixmap.
    """
    renderer = _renderer(name)
    if renderer is None:
        return QIcon()

    color = color or tp.get("accent_primary")
    pm = QPixmap(QSize(size, size))
    pm.fill(Qt.transparent)

    painter = QPainter(pm)
    renderer.render(painter)
    # Tint: paint the color over existing content, keeping alpha
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pm.rect(), QColor(color))
    painter.end()

    return QIcon(pm)


def themed_pixmap(name: str, color: str = "", size: int = 24) -> QPixmap:
    """Same as :func:`themed_icon` but returns a :class:`QPixmap` directly."""
    icon = themed_icon(name, color, size)
    return icon.pixmap(QSize(size, size))

"""Two-click distance measurement interaction mode.

Activates via Ctrl+M. First click sets the start tile, second click
completes the measurement and shows the path overlay + cost.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.engine.measure import measure_distance, format_measurement

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QGraphicsScene, QStatusBar
    from models.world.world_tile_manager import WorldTileManager
    from ui.tools.measure_overlay import MeasureOverlay


class MeasureMode:
    """Handles two-click distance measurement on the tile grid."""

    def __init__(
        self,
        scene: "QGraphicsScene",
        tile_map: "WorldTileManager",
        overlay: "MeasureOverlay",
        status_bar: "QStatusBar",
    ):
        self._scene = scene
        self._tile_map = tile_map
        self._overlay = overlay
        self._status_bar = status_bar
        self._start: tuple[int, int] | None = None
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    def toggle(self) -> None:
        """Toggle measure mode on/off."""
        if self._active:
            self.cancel()
        else:
            self._active = True
            self._status_bar.showMessage("Measure mode: click a start tile")

    def on_tile_clicked(self, position: tuple[int, int]) -> bool:
        """Handle a tile click. Returns True if consumed by measure mode.

        :param position: ``(row, col)`` of the clicked tile.
        :returns: True if the click was handled, False to pass through.
        """
        if not self._active:
            return False

        if self._start is None:
            self._start = position
            self._status_bar.showMessage(
                f"Measure from {position} — click destination (Esc to cancel)"
            )
            return True

        result = measure_distance(self._start, position, self._tile_map)
        if result.path is not None:
            self._overlay.show_path(result.path, result.cost_feet)
        self._status_bar.showMessage(format_measurement(result))
        self._start = None
        return True

    def cancel(self) -> None:
        """Cancel the current measurement and deactivate."""
        self._start = None
        self._overlay.clear()
        self._active = False
        self._status_bar.showMessage("")

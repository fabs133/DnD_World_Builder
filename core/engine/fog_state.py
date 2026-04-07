"""Fog of war state tracking.

Maintains which tiles have been seen (revealed) and which are currently
visible.  Pure data — no Qt dependency, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FogOfWarState:
    """Tracks per-faction tile visibility.

    :ivar revealed: Tiles that have been visible at some point.
    :ivar visible: Tiles that are visible *right now*.
    """

    revealed: set[tuple[int, int]] = field(default_factory=set)
    visible: set[tuple[int, int]] = field(default_factory=set)

    def update(self, newly_visible: set[tuple[int, int]]) -> None:
        """Recalculate visibility for this turn.

        :param newly_visible: The full set of tiles currently visible.
        """
        self.visible = newly_visible
        self.revealed |= newly_visible

    def get_tile_state(self, pos: tuple[int, int]) -> str:
        """Return the fog state for a single tile.

        :returns: ``"visible"``, ``"revealed"``, or ``"hidden"``.
        """
        if pos in self.visible:
            return "visible"
        if pos in self.revealed:
            return "revealed"
        return "hidden"

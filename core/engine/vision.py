"""Line of sight and fog of war on square and hex grids.

All functions are pure: they read tile data through a
:class:`~models.world.world_tile_manager.WorldTileManager`-like object
(``tile_type``, ``tiles`` mapping ``(row, col)`` to ``TileData``) and never
mutate it.

Coordinates are ``(row, col)``. Hex grids use the project's flat-top layout
where odd columns are shifted down by half a tile ("odd-q" offset
coordinates, see ``ui.main_window.hex_tile_center``).

Distances are in tiles. Square grids use Chebyshev distance (a diagonal step
counts as one tile, as in the D&D 5e default); hex grids use cube distance.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum
from typing import Any

from models.tiles.tile_data import TileTag

Position = tuple[int, int]

#: Vision range in tiles for entities without a ``vision_range`` (12 tiles = 60 ft).
DEFAULT_VISION_TILES = 12


class Visibility(Enum):
    """What a viewer knows about a tile."""

    HIDDEN = "hidden"  #: never seen
    EXPLORED = "explored"  #: seen before, not currently in view
    VISIBLE = "visible"  #: currently in view


# ----------------------------------------------------------------------
# Geometry
# ----------------------------------------------------------------------


def _to_cube(pos: Position) -> tuple[int, int, int]:
    row, col = pos
    q = col
    r = row - (col - (col & 1)) // 2
    return q, r, -q - r


def _from_cube(q: int, r: int) -> Position:
    col = q
    row = r + (q - (q & 1)) // 2
    return row, col


def _cube_round(q: float, r: float, s: float) -> tuple[int, int]:
    rq, rr, rs = round(q), round(r), round(s)
    dq, dr, ds = abs(rq - q), abs(rr - r), abs(rs - s)
    if dq > dr and dq > ds:
        rq = -rr - rs
    elif dr > ds:
        rr = -rq - rs
    return rq, rr


def grid_distance(a: Position, b: Position, tile_type: str) -> int:
    """Distance in tiles between two positions."""
    if tile_type == "hex":
        aq, ar, as_ = _to_cube(a)
        bq, br, bs = _to_cube(b)
        return max(abs(aq - bq), abs(ar - br), abs(as_ - bs))
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def line_between(a: Position, b: Position, tile_type: str) -> list[Position]:
    """Tiles on the straight line from ``a`` to ``b``, excluding ``a``, including ``b``."""
    steps = grid_distance(a, b, tile_type)
    if steps == 0:
        return []
    line = []
    if tile_type == "hex":
        aq, ar, as_ = _to_cube(a)
        bq, br, bs = _to_cube(b)
        # A tiny nudge keeps lines that run exactly along hex edges deterministic.
        eps = 1e-6
        for i in range(1, steps + 1):
            t = i / steps
            q = aq + (bq - aq) * t + eps
            r = ar + (br - ar) * t + eps
            s = as_ + (bs - as_) * t - 2 * eps
            line.append(_from_cube(*_cube_round(q, r, s)))
    else:
        for i in range(1, steps + 1):
            t = i / steps
            line.append((round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t)))
    return line


# ----------------------------------------------------------------------
# Line of sight
# ----------------------------------------------------------------------


def blocks_vision(tile: Any) -> bool:
    """True if ``tile`` (a ``TileData``) blocks line of sight."""
    return tile is not None and TileTag.BLOCKS_VISION in getattr(tile, "tags", ())


def can_see(viewer: Position, target: Position, tile_manager: Any, range_tiles: int) -> bool:
    """True if ``target`` is within ``range_tiles`` and no tile in between blocks vision.

    The target tile itself may block vision: a viewer can see a wall, just not
    what is behind it. Off-map targets are never visible.
    """
    tiles = tile_manager.tiles
    if target not in tiles:
        return False
    if grid_distance(viewer, target, tile_manager.tile_type) > range_tiles:
        return False
    between = line_between(viewer, target, tile_manager.tile_type)[:-1]
    return not any(blocks_vision(tiles.get(pos)) for pos in between)


def visible_positions(viewers: Iterable[tuple[Position, int]], tile_manager: Any) -> frozenset[Position]:
    """All tiles seen by at least one viewer.

    :param viewers: ``(position, range_tiles)`` pairs.
    :param tile_manager: Provides ``tiles`` and ``tile_type``.
    """
    seen: set[Position] = set()
    viewer_list = list(viewers)
    for pos in tile_manager.tiles:
        if any(can_see(viewer, pos, tile_manager, rng) for viewer, rng in viewer_list):
            seen.add(pos)
    return frozenset(seen)


def vision_range_tiles(entity: Any) -> int:
    """An entity's vision range in tiles (``vision_range`` attribute, else the default)."""
    value = getattr(entity, "vision_range", None)
    return DEFAULT_VISION_TILES if value is None else int(value)


# ----------------------------------------------------------------------
# Fog of war
# ----------------------------------------------------------------------


class FogOfWar:
    """Remembers which tiles a side has explored.

    Call :meth:`update` with the currently visible tiles (e.g. from
    :func:`visible_positions` over all player entities); then query
    :meth:`state` per tile.
    """

    def __init__(self) -> None:
        self._explored: set[Position] = set()
        self._visible: frozenset[Position] = frozenset()

    def update(self, visible: Iterable[Position]) -> None:
        self._visible = frozenset(visible)
        self._explored |= self._visible

    def reset(self) -> None:
        self._explored.clear()
        self._visible = frozenset()

    def state(self, pos: Position) -> Visibility:
        if pos in self._visible:
            return Visibility.VISIBLE
        if pos in self._explored:
            return Visibility.EXPLORED
        return Visibility.HIDDEN

"""Distance measurement between two coordinates on the tile grid.

Uses the A* pathfinder for path-aware distance and provides both
tile-count and feet-based results.  Pure functions — no Qt dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.engine.pathfinder import find_path, path_cost, _heuristic

if TYPE_CHECKING:
    from models.world.world_tile_manager import WorldTileManager


@dataclass(frozen=True)
class MeasureResult:
    """Result of a distance measurement between two points.

    :param start: Starting coordinate.
    :param end: Ending coordinate.
    :param path: List of coordinates along the shortest path (includes start/end),
                 or ``None`` if no path exists.
    :param cost_feet: Total movement cost in feet along the path, or -1 if unreachable.
    :param tile_count: Number of tiles in the path (including start), or 0 if unreachable.
    :param straight_line_tiles: Heuristic straight-line distance in tiles.
    """
    start: tuple[int, int]
    end: tuple[int, int]
    path: list[tuple[int, int]] | None
    cost_feet: int
    tile_count: int
    straight_line_tiles: int


def measure_distance(
    start: tuple[int, int],
    end: tuple[int, int],
    tile_map: "WorldTileManager",
) -> MeasureResult:
    """Compute the shortest-path distance between *start* and *end*.

    Returns a :class:`MeasureResult` with the path, cost in feet,
    tile count, and straight-line heuristic.

    :param start: Starting (row, col) coordinate.
    :param end: Ending (row, col) coordinate.
    :param tile_map: The tile manager providing adjacency and cost queries.
    :returns: Measurement result.
    """
    tile_type = getattr(tile_map, "tile_type", "square")
    straight = _heuristic(start, end, tile_type)

    if start == end:
        return MeasureResult(
            start=start,
            end=end,
            path=[start],
            cost_feet=0,
            tile_count=1,
            straight_line_tiles=0,
        )

    path = find_path(start, end, tile_map)

    if path is None:
        return MeasureResult(
            start=start,
            end=end,
            path=None,
            cost_feet=-1,
            tile_count=0,
            straight_line_tiles=straight,
        )

    cost = path_cost(path, tile_map)

    return MeasureResult(
        start=start,
        end=end,
        path=path,
        cost_feet=cost,
        tile_count=len(path),
        straight_line_tiles=straight,
    )


def format_measurement(result: MeasureResult) -> str:
    """Human-readable description of a measurement result.

    :param result: The measurement result to format.
    :returns: Formatted string like ``"Path: 4 tiles, 20ft (straight: 3 tiles)"``.
    """
    if result.path is None:
        return f"No path from {result.start} to {result.end}"

    if result.cost_feet == 0:
        return "Same tile (0ft)"

    return (
        f"Path: {result.tile_count} tiles, {result.cost_feet}ft "
        f"(straight: {result.straight_line_tiles} tiles)"
    )

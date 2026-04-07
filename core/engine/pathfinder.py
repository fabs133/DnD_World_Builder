"""A* pathfinding and reachability on the tile grid.

Pure functions — no Qt dependency, no I/O.  Works with both square and
hex grids via :class:`~models.world.world_tile_manager.WorldTileManager`.
"""

from __future__ import annotations

import heapq
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.world.world_tile_manager import WorldTileManager


def _heuristic(
    a: tuple[int, int],
    b: tuple[int, int],
    tile_type: str,
) -> int:
    """Admissible heuristic for the grid type.

    * **square** — Chebyshev distance (diagonals cost 1 step).
      Not used here since square grids only expose 4 cardinal neighbours,
      so Manhattan is both correct and admissible.
    * **hex** — offset-coordinate Manhattan ``(|dx| + |dy| + |dx - dy|) / 2``
      which equals cube distance for the flat-top offset layout used by the
      project.

    Returns the heuristic in *tiles* (not feet).
    """
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])

    if tile_type == "hex":
        # Cube distance for offset hex: convert to cube coords
        return (dx + dy + abs(dx - dy)) // 2
    # Square grid — 4-connected, so Manhattan is correct.
    return dx + dy


def find_path(
    start: tuple[int, int],
    goal: tuple[int, int],
    tile_map: "WorldTileManager",
    max_iterations: int = 10_000,
) -> list[tuple[int, int]] | None:
    """Return the shortest path from *start* to *goal*, or ``None``.

    Uses A* with the tile_map's adjacency, movement cost, and blocking
    queries.  The returned list **includes** *start* and *goal*.

    :param max_iterations: Safety cap to prevent runaway searches on
        very large or degenerate grids.
    """
    if start == goal:
        return [start]

    if tile_map.is_blocking(*goal):
        return None

    tile_type = tile_map.tile_type

    # Priority queue entries: (f_score, counter, coord)
    counter = 0
    open_set: list[tuple[int, int, tuple[int, int]]] = []
    heapq.heappush(open_set, (_heuristic(start, goal, tile_type), counter, start))

    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], int] = {start: 0}
    iterations = 0

    while open_set:
        iterations += 1
        if iterations > max_iterations:
            return None  # Safety cap exceeded

        _, _, current = heapq.heappop(open_set)

        if current == goal:
            return _reconstruct(came_from, current)

        for neighbour in tile_map.get_adjacent_tiles(*current):
            nx, ny = neighbour
            if tile_map.is_blocking(nx, ny):
                continue

            tentative_g = g_score[current] + tile_map.get_movement_cost(nx, ny)

            if tentative_g < g_score.get(neighbour, float("inf")):
                came_from[neighbour] = current
                g_score[neighbour] = tentative_g
                f = tentative_g + _heuristic(neighbour, goal, tile_type)
                counter += 1
                heapq.heappush(open_set, (f, counter, neighbour))

    return None  # No path exists


def reachable_tiles(
    origin: tuple[int, int],
    budget: int,
    tile_map: "WorldTileManager",
) -> dict[tuple[int, int], int]:
    """Dijkstra flood-fill: tiles reachable within *budget* movement cost.

    Returns ``{coord: cost_to_reach}`` — the origin is included with cost 0.
    """
    result: dict[tuple[int, int], int] = {origin: 0}

    # (cost, counter, coord)
    counter = 0
    heap: list[tuple[int, int, tuple[int, int]]] = [(0, counter, origin)]

    while heap:
        cost, _, current = heapq.heappop(heap)

        if cost > result.get(current, float("inf")):
            continue  # stale entry

        for neighbour in tile_map.get_adjacent_tiles(*current):
            nx, ny = neighbour
            if tile_map.is_blocking(nx, ny):
                continue

            new_cost = cost + tile_map.get_movement_cost(nx, ny)
            if new_cost > budget:
                continue

            if new_cost < result.get(neighbour, float("inf")):
                result[neighbour] = new_cost
                counter += 1
                heapq.heappush(heap, (new_cost, counter, neighbour))

    return result


def path_cost(
    path: list[tuple[int, int]],
    tile_map: "WorldTileManager",
) -> int:
    """Sum of movement costs along *path* (excludes the start tile)."""
    if len(path) < 2:
        return 0
    total = 0
    for x, y in path[1:]:
        total += tile_map.get_movement_cost(x, y)
    return total


def reachable_tiles_with_elevation(
    origin: tuple[int, int],
    budget: int,
    tile_map: "WorldTileManager",
    combat_grid: dict | None = None,
) -> dict[tuple[int, int], dict]:
    """Dijkstra flood-fill with elevation cost multipliers.

    Like :func:`reachable_tiles` but applies elevation-based cost
    modifiers from :func:`models.combat.elevation.evaluate_traversal`.

    Returns ``{coord: {"cost": int, "traversal_type": str}}`` for
    all reachable tiles within *budget*.

    :param combat_grid: Dict mapping ``(x, y)`` to TileData with elevation.
        If None, behaves identically to :func:`reachable_tiles`.
    """
    from models.combat.elevation import evaluate_traversal, TraversalType

    result: dict[tuple[int, int], dict] = {
        origin: {"cost": 0, "traversal_type": "flat"},
    }
    counter = 0
    heap: list[tuple[int, int, tuple[int, int]]] = [(0, counter, origin)]

    while heap:
        cost, _, current = heapq.heappop(heap)

        if cost > result.get(current, {}).get("cost", float("inf")):
            continue

        for neighbour in tile_map.get_adjacent_tiles(*current):
            nx, ny = neighbour
            if tile_map.is_blocking(nx, ny):
                continue

            base_cost = tile_map.get_movement_cost(nx, ny)

            # Apply elevation cost multiplier
            traversal_type = "flat"
            if combat_grid:
                from_tile = combat_grid.get(current)
                to_tile = combat_grid.get(neighbour)
                if from_tile and to_tile:
                    from_elev = getattr(from_tile, "elevation", 0)
                    to_elev = getattr(to_tile, "elevation", 0)
                    info = evaluate_traversal(from_elev, to_elev)
                    if info.traversal_type == TraversalType.IMPASSABLE:
                        continue
                    base_cost = int(base_cost * info.movement_cost_multiplier)
                    traversal_type = info.traversal_type.value

            new_cost = cost + base_cost
            if new_cost > budget:
                continue

            prev = result.get(neighbour, {}).get("cost", float("inf"))
            if new_cost < prev:
                result[neighbour] = {"cost": new_cost, "traversal_type": traversal_type}
                counter += 1
                heapq.heappush(heap, (new_cost, counter, neighbour))

    return result


def _reconstruct(
    came_from: dict[tuple[int, int], tuple[int, int]],
    current: tuple[int, int],
) -> list[tuple[int, int]]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path

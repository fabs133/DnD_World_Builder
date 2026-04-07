"""Visible tile computation for fog of war.

Uses the existing :meth:`~models.world.world.World.can_see` Bresenham
line-of-sight check.  Pure functions — no Qt dependency, no I/O.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.world.world import World


def compute_visible_tiles(
    world: "World",
    entity_positions_and_ranges: list[tuple[tuple[int, int], int]],
) -> set[tuple[int, int]]:
    """Compute the union of visible tiles for a set of observers.

    Each observer is specified as ``(position, vision_range)`` where
    *vision_range* is in **tiles** (Manhattan distance units matching
    ``World.can_see``).

    Uses ``world.can_see(from_pos, to_pos, max_range)`` for LOS checks.

    :param world: The World instance with tile_manager and ``can_see()``.
    :param entity_positions_and_ranges: List of ``((x, y), range)`` tuples.
    :returns: Set of ``(x, y)`` coordinates that are visible.
    """
    visible: set[tuple[int, int]] = set()
    tm = world.tile_manager
    width = tm.width
    height = tm.height

    for pos, vision_range in entity_positions_and_ranges:
        if vision_range <= 0:
            visible.add(pos)
            continue

        # Only check tiles within bounding box of the vision range
        px, py = pos
        x_min = max(0, px - vision_range)
        x_max = min(width - 1, px + vision_range)
        y_min = max(0, py - vision_range)
        y_max = min(height - 1, py + vision_range)

        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                if (x, y) not in visible:
                    if world.can_see(pos, (x, y), vision_range):
                        visible.add((x, y))

    return visible

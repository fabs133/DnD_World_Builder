"""Zone-aware entity filtering for encounter scoping.

Tiles can carry a ``zone_id`` (or fall back to ``user_label``) that groups
them into named encounter zones.  When combat triggers, only entities whose
position maps to the **same zone** as the triggering event participate in
initiative.  Entities in other zones remain dormant on the map.

Pure functions — no Qt dependency, no I/O.
"""

from __future__ import annotations

from typing import Optional, Sequence

from models.entities.entity_type import EntityType


# ------------------------------------------------------------------ #
# Zone map construction
# ------------------------------------------------------------------ #

def build_zone_map(tile_dicts: list[dict]) -> dict[tuple[int, int], Optional[str]]:
    """Build a ``{(row, col): zone_name}`` lookup from raw tile dicts.

    The zone is resolved as ``zone_id`` first, then ``user_label``.
    Tiles with neither are mapped to ``None``.
    """
    zone_map: dict[tuple[int, int], Optional[str]] = {}
    for td in tile_dicts:
        pos = tuple(td.get("position", (0, 0)))
        zone = td.get("zone_id") or td.get("user_label") or None
        zone_map[pos] = zone
    return zone_map


def has_any_zones(zone_map: dict[tuple[int, int], Optional[str]]) -> bool:
    """Return ``True`` if at least one tile has a non-``None`` zone."""
    return any(v is not None for v in zone_map.values())


# ------------------------------------------------------------------ #
# Lookups
# ------------------------------------------------------------------ #

def get_zone_at(
    zone_map: dict[tuple[int, int], Optional[str]],
    pos: tuple[int, int],
) -> Optional[str]:
    """Return the zone name for *pos*, or ``None`` if unzoned."""
    return zone_map.get(pos)


def zone_positions(
    zone_map: dict[tuple[int, int], Optional[str]],
    zone_name: str,
) -> frozenset[tuple[int, int]]:
    """Return all tile positions that belong to *zone_name*."""
    target = zone_name.strip().lower()
    return frozenset(
        pos for pos, z in zone_map.items()
        if z is not None and z.strip().lower() == target
    )


# ------------------------------------------------------------------ #
# Entity filtering
# ------------------------------------------------------------------ #

def entities_in_zone(
    all_entities: Sequence,
    zone_map: dict[tuple[int, int], Optional[str]],
    zone_name: str,
) -> list:
    """Return entities whose current position falls inside *zone_name*.

    Comparison is case-insensitive.  Entities without a position or on
    unzoned tiles are excluded.
    """
    positions = zone_positions(zone_map, zone_name)
    return [
        e for e in all_entities
        if getattr(e, "position", None) in positions
    ]


def nearby_combatants(
    all_entities: Sequence,
    center: tuple[int, int],
    radius: int = 5,
) -> list:
    """Proximity fallback: entities within *radius* tiles (Chebyshev).

    Player-type entities are **always** included regardless of distance
    so the party is never accidentally excluded.
    """
    cx, cy = center
    result: list = []
    for e in all_entities:
        pos = getattr(e, "position", None)
        if pos is None:
            continue
        dist = max(abs(pos[0] - cx), abs(pos[1] - cy))
        etype = getattr(e, "entity_type", "")
        if dist <= radius or etype in (EntityType.PLAYER, EntityType.ALLY, EntityType.COMPANION):
            result.append(e)
    return result

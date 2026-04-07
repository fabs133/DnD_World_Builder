"""Utility functions for entity list processing. No Qt imports."""

from __future__ import annotations

from collections import Counter
from typing import Sequence

from models.entities.entity_type import EntityType

# Entity types that participate in combat turns.
# Because EntityType inherits from str, plain-string comparisons still work.
_COMBATANT_TYPES = frozenset({
    EntityType.PLAYER, EntityType.ENEMY, EntityType.NPC,
    EntityType.MONSTER, EntityType.HOSTILE, EntityType.ALLY,
    EntityType.COMPANION,
})


def disambiguate_names(entities: Sequence) -> None:
    """Append numeric suffixes to entities that share a name.

    Mutates ``entity.name`` in-place.
    Single instances keep their original name unchanged.

    Example::

        [Wolf, Wolf, Wolf, Goblin] -> [Wolf 1, Wolf 2, Wolf 3, Goblin]
    """
    name_counts = Counter(getattr(e, "name", "") for e in entities)
    duplicates = {name for name, count in name_counts.items() if count > 1}

    if not duplicates:
        return

    counters: dict[str, int] = {name: 0 for name in duplicates}

    for entity in entities:
        name = getattr(entity, "name", "")
        if name in duplicates:
            counters[name] += 1
            entity.name = f"{name} {counters[name]}"


def is_combatant(entity) -> bool:
    """Check if a single entity should participate in the turn order."""
    entity_type = getattr(entity, "entity_type", "")

    if entity_type not in _COMBATANT_TYPES:
        return False

    # Dead entities don't take turns
    hp = getattr(entity, "hp", None)
    if hp is not None and hp <= 0:
        return False

    return True


def filter_combatants(entities: Sequence) -> list:
    """Return only entities that should participate in initiative.

    Filters out items, objects, traps, scenery, and dead entities.
    Non-combatants still exist in the world for rendering — they just
    don't take turns.
    """
    return [e for e in entities if is_combatant(e)]

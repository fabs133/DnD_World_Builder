"""Shared combat utility functions for AI adapters.

Extracted from :class:`AIAdapter` and :class:`HeuristicAIAdapter` to
eliminate duplication.  All functions are pure — no I/O, no Qt dependency.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.engine.game_state import GameState, EntitySnapshot
    from models.ai.personality import EntityPersonality


# ── Faction logic ────────────────────────────────────────────────────────

_PLAYER_TYPES = frozenset({"player", "ally", "companion"})
_ENEMY_TYPES = frozenset({"enemy", "monster", "hostile"})


def are_allies(type_a: str, type_b: str) -> bool:
    """Check if two entity types are on the same faction.

    :param type_a: First entity type (lowercase).
    :param type_b: Second entity type (lowercase).
    :returns: True if both are player-faction or both are enemy-faction.
    """
    a_player = type_a in _PLAYER_TYPES
    b_player = type_b in _PLAYER_TYPES
    a_enemy = type_a in _ENEMY_TYPES
    b_enemy = type_b in _ENEMY_TYPES
    return (a_player and b_player) or (a_enemy and b_enemy)


def get_enemies(
    actor_name: str,
    actor_type: str,
    game_state: "GameState",
) -> list["EntitySnapshot"]:
    """Return alive enemies of *actor_name*.

    :param actor_name: Name of the acting entity (excluded from results).
    :param actor_type: Entity type of the actor (e.g. ``"enemy"``).
    :param game_state: Current game state snapshot.
    """
    enemies = []
    for snap in game_state.entities:
        if snap.name == actor_name or not snap.is_alive:
            continue
        if not are_allies(actor_type.lower(), snap.entity_type.lower()):
            enemies.append(snap)
    return enemies


# ── Target selection ─────────────────────────────────────────────────────


def find_weakest_target(
    valid_targets: list[str],
    game_state: "GameState",
) -> str:
    """Return the name of the target with lowest HP.

    :param valid_targets: Names to choose from (must be non-empty).
    :param game_state: Current game state snapshot.
    """
    weakest = valid_targets[0]
    lowest_hp = float("inf")
    for snap in game_state.entities:
        if snap.name in valid_targets and snap.hp < lowest_hp:
            lowest_hp = snap.hp
            weakest = snap.name
    return weakest


# ── Entity / personality lookup ──────────────────────────────────────────


def get_actor(entity_name: str, entities_by_name: dict[str, Any]) -> Any:
    """Get an entity reference, returning a lightweight stub if missing.

    :param entity_name: Name to look up.
    :param entities_by_name: Entity registry dict.
    """
    if entity_name in entities_by_name:
        return entities_by_name[entity_name]

    class _Stub:
        name = entity_name
        entity_type = "creature"
        hp = 10
        max_hp = 10
        position = (0, 0)
        personality = None

    return _Stub()


def get_personality(
    actor: Any,
    default_personality: "EntityPersonality",
) -> "EntityPersonality":
    """Get personality from an actor, falling back to *default_personality*.

    :param actor: The entity object.
    :param default_personality: Fallback personality.
    """
    personality = getattr(actor, "personality", None)
    if personality is not None:
        return personality
    return default_personality

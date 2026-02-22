"""
State Synchronization
=====================

Pure functions for serializing world state and computing deltas.

The delta sync cycle works as follows:

1. :func:`serialize_world` captures the current world as a plain dict.
2. :func:`compute_delta` diffs two snapshots, producing a change list.
3. :func:`apply_delta` patches a snapshot with a change list.

The key invariant is::

    apply_delta(old, compute_delta(old, new)) == new
"""

import copy


def serialize_world(world) -> dict:
    """Serialize a :class:`~models.world.world.World` to a dict for network transmission.

    Reuses existing ``TileData.to_dict()`` and ``GameEntity.to_dict()``.

    :param world: The world object to serialize.
    :type world: ~models.world.world.World
    :return: A dict containing ``tiles``, ``entities``, ``lore``, and ``turn`` keys.
    :rtype: dict
    """
    tiles = {}
    for pos, tile_data in world.tile_manager.tiles.items():
        key = f"{pos[0]},{pos[1]}"
        tiles[key] = tile_data.to_dict()

    entities = {}
    for pos, entity_list in world.tile_manager.entities.items():
        key = f"{pos[0]},{pos[1]}"
        entities[key] = [e.to_dict() for e in entity_list]

    return {
        "width": world.tile_manager.width,
        "height": world.tile_manager.height,
        "tile_type": world.tile_manager.tile_type,
        "tiles": tiles,
        "entities": entities,
        "lore": {
            "description": world.lore.description,
            "time_of_day": world.lore.time_of_day,
            "weather_conditions": world.lore.weather_conditions,
        },
        "turn": {
            "current_turn": world.turn_manager.current_turn,
        },
    }


def serialize_entity(entity) -> dict:
    """Serialize a single :class:`~models.entities.game_entity.GameEntity`.

    Includes position if set on the entity.

    :param entity: The entity to serialize.
    :type entity: ~models.entities.game_entity.GameEntity
    :return: A dict representation with an optional ``position`` key.
    :rtype: dict
    """
    data = entity.to_dict()
    if hasattr(entity, "position") and entity.position is not None:
        data["position"] = list(entity.position)
    return data


def compute_delta(old_state: dict, new_state: dict) -> list:
    """Compute a list of changes between two serialized world states.

    Uses key-level diffing on tiles, entities, lore, and turn sections.
    Each change dict has keys ``op``, ``path``, and (for add/update) ``value``.

    :param old_state: Previous state snapshot from :func:`serialize_world`.
    :type old_state: dict
    :param new_state: Current state snapshot from :func:`serialize_world`.
    :type new_state: dict
    :return: A list of change dicts, each with ``op`` (``"add"``/``"update"``/``"remove"``),
        ``path`` (e.g. ``"tiles/0,1"``), and optionally ``value``.
    :rtype: list[dict]
    """
    changes = []

    for section in ("tiles", "entities"):
        old_section = old_state.get(section, {})
        new_section = new_state.get(section, {})
        for key in set(old_section.keys()) | set(new_section.keys()):
            if key not in old_section:
                changes.append({"op": "add", "path": f"{section}/{key}", "value": new_section[key]})
            elif key not in new_section:
                changes.append({"op": "remove", "path": f"{section}/{key}"})
            elif old_section[key] != new_section[key]:
                changes.append({"op": "update", "path": f"{section}/{key}", "value": new_section[key]})

    for top_key in ("lore", "turn"):
        old_val = old_state.get(top_key, {})
        new_val = new_state.get(top_key, {})
        if old_val != new_val:
            changes.append({"op": "update", "path": top_key, "value": new_val})

    return changes


def apply_delta(state: dict, changes: list) -> dict:
    """Apply a change list to a serialized state, returning a new dict.

    Does not mutate the input; returns a deep copy with changes applied.

    :param state: The base state to patch.
    :type state: dict
    :param changes: Change list from :func:`compute_delta`.
    :type changes: list[dict]
    :return: A new state dict with changes applied.
    :rtype: dict
    """
    result = copy.deepcopy(state)

    for change in changes:
        op = change["op"]
        path = change["path"]
        parts = path.split("/", 1)

        if len(parts) == 1:
            if op in ("update", "add"):
                result[parts[0]] = change["value"]
            elif op == "remove":
                result.pop(parts[0], None)
        elif len(parts) == 2:
            container_key, item_key = parts
            container = result.setdefault(container_key, {})
            if op in ("update", "add"):
                container[item_key] = change["value"]
            elif op == "remove":
                container.pop(item_key, None)

    return result

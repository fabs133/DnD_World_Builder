"""Zone interaction logic — determines available interactions for entities."""

from __future__ import annotations

from typing import Any, List

from models.entities.entity_type import EntityType


def get_available_interactions(entity: Any, viewer_role: str = "player") -> List[dict]:
    """Determine what a player can do with an entity.

    Returns list of dicts: {id, label, enabled, reason}.
    """
    etype = getattr(entity, "entity_type", "")
    tags = getattr(entity, "tags", [])
    if isinstance(tags, str):
        tags = [tags]
    hp = getattr(entity, "hp", 1)
    is_dm = viewer_role == "dm"

    interactions = []

    # All entities can be inspected
    interactions.append({"id": "inspect", "label": "Inspect", "enabled": True, "reason": ""})

    # NPCs
    if etype in ("npc", "ally", "enemy", "companion", "player"):
        can_talk = hp > 0 or is_dm
        interactions.append({
            "id": "talk", "label": "Talk",
            "enabled": can_talk,
            "reason": "" if can_talk else "This entity is unconscious",
        })

        if "merchant" in tags or "shopkeeper" in tags:
            interactions.append({"id": "trade", "label": "Trade", "enabled": True, "reason": ""})

    # Objects
    if etype == "object":
        interactions.append({"id": "search", "label": "Search", "enabled": True, "reason": ""})

        if "container" in tags:
            interactions.append({"id": "open", "label": "Open", "enabled": True, "reason": ""})
        if "readable" in tags:
            interactions.append({"id": "read", "label": "Read", "enabled": True, "reason": ""})
        if "usable" in tags:
            interactions.append({"id": "use", "label": "Use", "enabled": True, "reason": ""})
        if "item" in tags:
            interactions.append({"id": "pickup", "label": "Pick Up", "enabled": True, "reason": ""})
        if getattr(entity, "locked", False):
            interactions.append({"id": "pick_lock", "label": "Pick Lock", "enabled": True, "reason": ""})

    return interactions


def get_inspect_text(entity: Any) -> str:
    """Generate inspection text for an entity."""
    etype = getattr(entity, "entity_type", "unknown")
    name = getattr(entity, "name", "Unknown")
    lines = [f"{name} ({etype})"]

    desc = getattr(entity, "description", None)
    if desc:
        lines.append(desc)

    hp = getattr(entity, "hp", None)
    max_hp = getattr(entity, "max_hp", None)
    if hp is not None and max_hp is not None:
        if hp >= max_hp:
            lines.append("Appears healthy.")
        elif hp > max_hp * 0.5:
            lines.append("Shows signs of injury.")
        elif hp > 0:
            lines.append("Badly wounded.")
        else:
            lines.append("Unconscious or dead.")

    return "\n".join(lines)

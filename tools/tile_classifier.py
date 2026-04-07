"""Classify a serialized tile dict by narrative purpose.

Five categories drive different prompt-enrichment strategies:

- **narrative**  : at least one dialogue-bearing NPC
- **riddle**     : an ENTER_TILE trigger with a non-damage reaction, no enemies
- **boss**       : 1-2 distinct named enemies
- **pack**       : 3+ enemies, or repeated generic enemies
- **transit**    : empty / scenery-only tiles (the default)

An explicit ``tile["tile_type"]`` field always wins over the heuristic,
letting authors force a specific classification on tricky tiles.
"""

from __future__ import annotations

from typing import Any

# Tile type constants (used as both dict keys and return values)
NARRATIVE = "narrative"
RIDDLE = "riddle"
BOSS = "boss"
PACK = "pack"
TRANSIT = "transit"

VALID_TYPES = frozenset({NARRATIVE, RIDDLE, BOSS, PACK, TRANSIT})

# Entity types that count as "social" — their presence pushes a tile
# toward NARRATIVE classification.
_SOCIAL_TYPES = frozenset({"npc", "player", "ally", "companion"})

# Entity types that count as combat opponents.
_ENEMY_TYPES = frozenset({"enemy", "monster", "hostile"})

# Names that indicate a generic creature (not a distinct boss). Used to
# downgrade tiles from BOSS to PACK when the single enemy is e.g. a
# Goblin rather than "Grishak the Foul".
_GENERIC_NAME_STEMS = frozenset({
    "goblin", "orc", "kobold", "wolf", "rat", "bat", "spider", "bandit",
    "skeleton", "zombie", "cultist", "guard", "thug", "wasp", "snake",
    "dire wolf", "giant rat", "giant spider", "ghoul", "ghost", "shade",
    "imp", "slime", "bear", "boar",
})


# ── Helpers ────────────────────────────────────────────────────────────


def _entity_type(entity: dict) -> str:
    """Return the entity_type string, lowercased, or empty."""
    etype = entity.get("entity_type", "")
    if isinstance(etype, str):
        return etype.lower()
    # Enum-like object fallback
    return str(getattr(etype, "value", etype)).lower()


def _is_generic_name(name: str) -> bool:
    """True if *name* matches a known generic creature stem."""
    if not name:
        return True
    low = name.strip().lower()
    # Exact stem match, or name equals stem (e.g. "Goblin")
    if low in _GENERIC_NAME_STEMS:
        return True
    # Match stems that appear as the entire name with optional
    # prefix adjectives ("Dire Wolf" -> "wolf" is a stem, check
    # the last token as well).
    last = low.split()[-1] if low.split() else low
    return last in _GENERIC_NAME_STEMS


def _has_dialogue(entity: dict) -> bool:
    dlg = entity.get("dialogue_lines")
    if isinstance(dlg, dict) and dlg:
        return True
    if isinstance(dlg, list) and dlg:
        return True
    return False


def _collect_enemies(tile: dict) -> list[dict]:
    return [
        e for e in tile.get("entities", [])
        if _entity_type(e) in _ENEMY_TYPES
    ]


def _collect_socials(tile: dict) -> list[dict]:
    return [
        e for e in tile.get("entities", [])
        if _entity_type(e) in _SOCIAL_TYPES
    ]


def _has_event_trigger(tile: dict) -> bool:
    """True if tile has an ENTER_TILE trigger whose reaction is NOT
    a damage/trap reaction (``ApplyDamage``)."""
    for trig in tile.get("triggers", []) or []:
        if not isinstance(trig, dict):
            continue
        if trig.get("event_type") != "ENTER_TILE":
            continue
        reaction = trig.get("reaction") or {}
        if isinstance(reaction, dict):
            rtype = reaction.get("type", "")
            if rtype != "ApplyDamage":
                return True
    return False


# ── Public API ─────────────────────────────────────────────────────────


def classify_tile(tile: dict) -> str:
    """Return the classified tile type.

    Rules (first match wins):
    1. Explicit ``tile_type`` override, if valid.
    2. NARRATIVE: any social entity with dialogue_lines.
    3. RIDDLE: event trigger with non-damage reaction, no enemies.
    4. BOSS: 1-2 enemies, all with distinct non-generic names.
    5. PACK: 3+ enemies or repeated/generic enemy names.
    6. TRANSIT: everything else.
    """
    # 1. Explicit override
    override = tile.get("tile_type")
    if isinstance(override, str) and override in VALID_TYPES:
        return override

    enemies = _collect_enemies(tile)
    socials = _collect_socials(tile)

    # 2. NARRATIVE — dialogue-bearing social entity present
    for s in socials:
        if _has_dialogue(s):
            return NARRATIVE

    # 3. RIDDLE — event trigger, no enemies
    if not enemies and _has_event_trigger(tile):
        return RIDDLE

    # 4/5. Enemy-based classification
    if enemies:
        names = [e.get("name", "") for e in enemies]
        unique_names = set(n.strip().lower() for n in names if n)
        all_distinct = len(unique_names) == len(enemies)
        any_generic = any(_is_generic_name(n) for n in names)

        if len(enemies) <= 2 and all_distinct and not any_generic:
            return BOSS
        return PACK

    # 6. TRANSIT default
    return TRANSIT


def find_pack_lead(tile: dict) -> dict | None:
    """Return a single distinguished "lead" enemy for a PACK tile.

    A lead is an enemy whose name is NOT generic while at least one other
    enemy on the tile has a generic name (or shares a name). Returns
    ``None`` when the pack is uniformly generic or uniformly distinct.
    """
    enemies = _collect_enemies(tile)
    if len(enemies) < 2:
        return None

    names = [e.get("name", "") for e in enemies]
    generic_flags = [_is_generic_name(n) for n in names]

    # Need at least one generic AND at least one non-generic to call
    # the non-generic a "lead".
    if not any(generic_flags) or all(generic_flags):
        return None

    # Pick the first non-generic entry. If several non-generics exist,
    # prefer the one that is not repeated.
    non_generic_indices = [i for i, g in enumerate(generic_flags) if not g]
    if not non_generic_indices:
        return None

    # Return the first non-generic entity
    return enemies[non_generic_indices[0]]

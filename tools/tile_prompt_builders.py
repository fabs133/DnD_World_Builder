"""Per-tile-type prompt builders.

Each builder takes a serialized tile dict, the biome lexicon, and a
shared biome hint string, and returns a list of prompt phrases. The
main composer in :mod:`tile_background_generator` concatenates these
with the style suffix and edge-structure phrases.

Design notes:
- All builders are pure functions.
- Lexicon sampling is deterministic per (biome_key, tile_seed) so the
  same tile always receives the same phrases across runs.
- Empty or missing lexicon entries gracefully degrade — builders still
  return a valid prompt using terrain and narrator hints.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

try:
    from tools.tile_classifier import (
        NARRATIVE, RIDDLE, BOSS, PACK, TRANSIT,
        find_pack_lead,
    )
    from tools.regional_workflow import RegionalPrompt
    from tools.tile_background_generator import _NEGATIVE_PEOPLE_BACKGROUND, _STYLE_SUFFIX
except ImportError:  # pragma: no cover
    from tile_classifier import (  # type: ignore
        NARRATIVE, RIDDLE, BOSS, PACK, TRANSIT,
        find_pack_lead,
    )
    from regional_workflow import RegionalPrompt  # type: ignore
    from tile_background_generator import _NEGATIVE_PEOPLE_BACKGROUND, _STYLE_SUFFIX  # type: ignore


# Reuse the terrain phrases dict from the main generator module. We
# import lazily inside the helpers to avoid a circular import at module
# load time.

_NPC_TYPES = {"npc", "player", "ally", "companion"}
_ENEMY_TYPES = {"enemy", "monster", "hostile"}


# ── Shared helpers ─────────────────────────────────────────────────────


def _terrain_phrase(tile: dict) -> str:
    """Look up the terrain phrase, mirroring the main generator."""
    try:
        from tools.tile_background_generator import _TERRAIN_PHRASES, _tile_terrain
    except ImportError:  # pragma: no cover
        from tile_background_generator import _TERRAIN_PHRASES, _tile_terrain  # type: ignore
    terrain = _tile_terrain(tile)
    return _TERRAIN_PHRASES.get(terrain, f"{terrain} terrain")


def _zone_label(tile: dict) -> str:
    try:
        from tools.tile_background_generator import _tile_zone_label
    except ImportError:  # pragma: no cover
        from tile_background_generator import _tile_zone_label  # type: ignore
    return _tile_zone_label(tile)


def _biome_key_from_tile(tile: dict) -> str:
    """Derive a biome key from the tile dict.

    Priority order:
    1. ``tile["biome_key"]`` — set by the runner before calling the builder
       (robust against background_image edits from prior runs).
    2. ``tile["background_image"]`` stem, when the path points at
       ``assets/backgrounds/`` (the un-edited original biome image).
    3. Empty string (no lexicon garnish).
    """
    key = tile.get("biome_key")
    if isinstance(key, str) and key:
        return key

    bg = tile.get("background_image") or ""
    if bg and "assets/backgrounds/" in bg:
        return Path(bg).stem
    return ""


def _tile_seed_key(tile: dict) -> str:
    """Stable string key for deterministic lexicon sampling."""
    pos = tile.get("position", [0, 0])
    try:
        x, y = int(pos[0]), int(pos[1])
    except (TypeError, ValueError, IndexError):
        x, y = 0, 0
    return f"{x}_{y}"


def _deterministic_indices(seed_key: str, n: int, pool_size: int) -> list[int]:
    """Return up to *n* distinct indices into a pool of *pool_size*,
    chosen deterministically from the seed key."""
    if pool_size <= 0 or n <= 0:
        return []
    n = min(n, pool_size)
    # Hash the seed key + an increasing salt to get stable indices.
    picked: list[int] = []
    salt = 0
    tried = 0
    max_tries = pool_size * 4
    while len(picked) < n and tried < max_tries:
        h = hashlib.sha256(f"{seed_key}:{salt}".encode()).digest()
        idx = int.from_bytes(h[:4], "big") % pool_size
        if idx not in picked:
            picked.append(idx)
        salt += 1
        tried += 1
    return picked


def _sample_lexicon(
    lexicon: dict,
    biome_key: str,
    seed_key: str,
    category: str,
    count: int,
) -> list[str]:
    """Pick *count* entries from ``lexicon[biome_key][category]``.

    Silently returns an empty list for missing keys or empty categories.
    Results are deterministic per (seed_key, category).
    """
    if not lexicon or not biome_key:
        return []
    biome = lexicon.get(biome_key) or {}
    pool = biome.get(category) or []
    if not pool:
        return []
    # Use category in the salt so silhouettes and landmarks don't
    # collide on the same indices for the same tile.
    indices = _deterministic_indices(f"{seed_key}:{category}", count, len(pool))
    return [pool[i] for i in indices]


def _lexicon_palette(lexicon: dict, biome_key: str) -> str:
    return ((lexicon or {}).get(biome_key, {}).get("palette") or "").strip()


def _lexicon_mood(lexicon: dict, biome_key: str) -> str:
    return ((lexicon or {}).get(biome_key, {}).get("mood") or "").strip()


def _entity_descriptor(entity: dict) -> str:
    """Compose a short visual descriptor for an entity.

    Prefers an authored ``flavor_description`` field if present; otherwise
    derives a natural-language phrase from the entity's name. Named
    characters (anything not matching a generic creature stem) retain
    their original casing so proper nouns survive into the prompt.
    """
    flavor = (entity.get("flavor_description") or "").strip()
    if flavor:
        return flavor
    name = (entity.get("name") or "").strip()
    if not name:
        return "an unknown figure"

    # Late import so we share the canonical generic-name stopword list.
    try:
        from tools.tile_classifier import _is_generic_name
    except ImportError:  # pragma: no cover
        from tile_classifier import _is_generic_name  # type: ignore

    if _is_generic_name(name):
        # Generic creatures become lowercase noun phrases.
        return f"a {name.lower()}"
    # Named characters preserve their original casing.
    return f"a figure known as {name}"


def _generic_group_name(enemies: list[dict]) -> str:
    """Pick a representative generic-plural name for a pack."""
    if not enemies:
        return "creatures"
    # Find the most common name
    counts: dict[str, int] = {}
    for e in enemies:
        n = (e.get("name") or "").strip()
        if n:
            counts[n] = counts.get(n, 0) + 1
    if not counts:
        return "creatures"
    most_common = max(counts.items(), key=lambda kv: kv[1])[0]
    lower = most_common.lower()
    # naive plural
    if lower.endswith("s"):
        return lower
    if lower.endswith("y"):
        return lower[:-1] + "ies"
    return lower + "s"


def _narrator_intro(tile: dict) -> str:
    return (tile.get("narrator_intro") or "").strip()


# ── Builders ───────────────────────────────────────────────────────────


def build_narrative_phrases(
    tile: dict,
    lexicon: dict,
    biome_hint: str,
) -> RegionalPrompt:
    """Rich social scene with spatially separated regions.

    Returns a :class:`RegionalPrompt` so each visual element gets its
    own conditioning mask. The NPC is isolated in the center region,
    preventing feature merging with landmarks or animals.
    """
    socials = [
        e for e in tile.get("entities", [])
        if (e.get("entity_type") or "").lower() in _NPC_TYPES
    ]
    biome_key = _biome_key_from_tile(tile)
    seed_key = _tile_seed_key(tile)
    narrator = _narrator_intro(tile)

    # Center: primary NPC subject
    if socials:
        lead_desc = _entity_descriptor(socials[0])
        if len(socials) > 1:
            center = (f"{lead_desc} as the central figure, full body visible, complete arms and legs, medium distance, "
                      f"with shadowy companions standing in the background")
        else:
            center = f"{lead_desc} as the central figure, full body visible, complete arms and legs, medium distance"
    else:
        center = "a solitary figure standing in the scene"

    # Left/Right: atmospheric scene-setting — NOT concrete objects.
    # "A sagging wooden inn" generates a distinct building that fights the
    # figure. Instead we want vague environmental flavor that blends
    # naturally at the region boundary.
    left_items = _sample_lexicon(lexicon, biome_key, seed_key, "landmarks", 1)
    left_hint = left_items[0] if left_items else ""
    left = f"blurred background scenery, {left_hint}" if left_hint else "soft atmospheric background detail"

    right_items = _sample_lexicon(lexicon, biome_key, seed_key, "silhouettes", 1)
    right_hint = right_items[0] if right_items else ""
    right = f"distant background detail, {right_hint}" if right_hint else "ambient environmental scenery"

    # Base: unifying palette, mood, biome — applies at low weight everywhere
    base_parts: list[str] = []
    if biome_hint:
        base_parts.append(biome_hint.strip())
    if narrator:
        base_parts.append(narrator)
    palette = _lexicon_palette(lexicon, biome_key)
    if palette:
        base_parts.append(palette)
    mood = _lexicon_mood(lexicon, biome_key)
    if mood:
        base_parts.append(mood)
    base_parts.append(_STYLE_SUFFIX)
    base = ", ".join(base_parts)

    return RegionalPrompt(
        base=base,
        center=center,
        left=left,
        right=right,
        negative=_NEGATIVE_PEOPLE_BACKGROUND,
    )


def build_event_phrases(
    tile: dict,
    lexicon: dict,
    biome_hint: str,
) -> list[str]:
    """Event tile: focus on the trigger, minimal biome garnish."""
    phrases: list[str] = []
    if biome_hint:
        phrases.append(biome_hint.strip())

    narrator = _narrator_intro(tile)
    if narrator:
        phrases.append(narrator)
    else:
        # Derive a placeholder focal object from the trigger label
        for trig in tile.get("triggers") or []:
            if isinstance(trig, dict) and trig.get("event_type") == "ENTER_TILE":
                label = (trig.get("label") or "").replace("_", " ").strip()
                if label:
                    phrases.append(f"at the center, a scene of {label}")
                    break

    biome_key = _biome_key_from_tile(tile)
    seed_key = _tile_seed_key(tile)
    phrases.extend(_sample_lexicon(lexicon, biome_key, seed_key, "landmarks", 1))

    palette = _lexicon_palette(lexicon, biome_key)
    if palette:
        phrases.append(palette)

    return phrases


def build_boss_phrases(
    tile: dict,
    lexicon: dict,
    biome_hint: str,
) -> RegionalPrompt:
    """Boss tile: dominant figure in center, environment flanking."""
    enemies = [
        e for e in tile.get("entities", [])
        if (e.get("entity_type") or "").lower() in _ENEMY_TYPES
    ]
    biome_key = _biome_key_from_tile(tile)
    seed_key = _tile_seed_key(tile)
    narrator = _narrator_intro(tile)

    if enemies:
        lead = _entity_descriptor(enemies[0])
        if len(enemies) >= 2:
            center = (f"a towering presence: {lead}, full body visible, complete arms and legs, "
                      f"with another dark silhouette looming at their flank")
        else:
            center = f"a towering presence: {lead}, full body visible, complete arms and legs"
    else:
        center = "a menacing presence dominating the scene"

    left_items = _sample_lexicon(lexicon, biome_key, seed_key, "silhouettes", 1)
    left_hint = left_items[0] if left_items else ""
    left = f"blurred ominous background, {left_hint}" if left_hint else "dark atmospheric background"

    right_items = _sample_lexicon(lexicon, biome_key, seed_key, "landmarks", 1)
    right_hint = right_items[0] if right_items else ""
    right = f"distant environmental detail, {right_hint}" if right_hint else "ambient dark scenery"

    base_parts: list[str] = []
    if biome_hint:
        base_parts.append(biome_hint.strip())
    if narrator:
        base_parts.append(narrator)
    palette = _lexicon_palette(lexicon, biome_key)
    if palette:
        base_parts.append(palette)
    mood = _lexicon_mood(lexicon, biome_key)
    if mood:
        base_parts.append(mood)
    base_parts.append(_STYLE_SUFFIX)
    base = ", ".join(base_parts)

    return RegionalPrompt(
        base=base,
        center=center,
        left=left,
        right=right,
        negative=_NEGATIVE_PEOPLE_BACKGROUND,
    )


def build_pack_phrases(
    tile: dict,
    lexicon: dict,
    biome_hint: str,
) -> RegionalPrompt:
    """Pack tile: lead figure in center, lesser shapes flanking."""
    enemies = [
        e for e in tile.get("entities", [])
        if (e.get("entity_type") or "").lower() in _ENEMY_TYPES
    ]
    biome_key = _biome_key_from_tile(tile)
    seed_key = _tile_seed_key(tile)
    lead = find_pack_lead(tile)

    if lead is not None:
        center = (f"{_entity_descriptor(lead)} as the central figure, "
                  f"with a group of lesser shapes prowling at a distance")
    elif enemies:
        plural = _generic_group_name(enemies)
        center = f"a group of {plural} at medium distance, indistinct figures"
    else:
        center = "vague shapes lurking in the distance"

    left_items = _sample_lexicon(lexicon, biome_key, seed_key, "silhouettes", 1)
    left_hint = left_items[0] if left_items else ""
    left = f"blurred background scenery, {left_hint}" if left_hint else "ambient background scenery"

    right_items = _sample_lexicon(lexicon, biome_key, seed_key, "landmarks", 1)
    right_hint = right_items[0] if right_items else ""
    right = f"distant background detail, {right_hint}" if right_hint else "environmental background detail"

    base_parts: list[str] = []
    if biome_hint:
        base_parts.append(biome_hint.strip())
    palette = _lexicon_palette(lexicon, biome_key)
    if palette:
        base_parts.append(palette)
    base_parts.append(_STYLE_SUFFIX)
    base = ", ".join(base_parts)

    return RegionalPrompt(
        base=base,
        center=center,
        left=left,
        right=right,
        negative=_NEGATIVE_PEOPLE_BACKGROUND,
    )


def build_transit_phrases(
    tile: dict,
    lexicon: dict,
    biome_hint: str,
) -> list[str]:
    """Transit tile: the baseline — biome hint, optional narrator,
    zone label, terrain, and one lexicon garnish."""
    phrases: list[str] = []
    if biome_hint:
        phrases.append(biome_hint.strip())

    # Honour narrator_intro when authored, even on transit tiles —
    # if the author wrote it, they want it in the image.
    narrator = _narrator_intro(tile)
    if narrator:
        phrases.append(narrator)

    zone_label = _zone_label(tile)
    if zone_label:
        phrases.append(zone_label.strip())

    phrases.append(_terrain_phrase(tile))

    biome_key = _biome_key_from_tile(tile)
    seed_key = _tile_seed_key(tile)
    # Alternate between landmark and silhouette deterministically
    h = hashlib.sha256(seed_key.encode()).digest()[0]
    category = "landmarks" if h % 2 == 0 else "silhouettes"
    phrases.extend(_sample_lexicon(lexicon, biome_key, seed_key, category, 1))

    return phrases


# ── Dispatcher ─────────────────────────────────────────────────────────


BUILDERS = {
    NARRATIVE: build_narrative_phrases,
    RIDDLE: build_event_phrases,
    BOSS: build_boss_phrases,
    PACK: build_pack_phrases,
    TRANSIT: build_transit_phrases,
}

"""Unit tests for the tile classifier.

Covers every rule in :func:`tools.tile_classifier.classify_tile`:
- explicit override
- NARRATIVE (social entity with dialogue)
- RIDDLE (non-damage ENTER_TILE trigger, no enemies)
- BOSS (1-2 unique non-generic enemies)
- PACK (3+ enemies OR repeated/generic names)
- TRANSIT (everything else)

Plus edge cases: empty tiles, damage triggers downgrading to transit,
social + enemies on the same tile, and ``find_pack_lead`` for mixed packs.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent.parent.parent / "tools"),
)

from tile_classifier import (  # noqa: E402
    classify_tile,
    find_pack_lead,
    NARRATIVE,
    RIDDLE,
    BOSS,
    PACK,
    TRANSIT,
)


# ── Helpers ────────────────────────────────────────────────────────────


def _tile(**kwargs) -> dict:
    base = {"position": [0, 0], "terrain": "GRASS", "entities": [], "triggers": []}
    base.update(kwargs)
    return base


def _npc(name: str, dialogue=True) -> dict:
    e = {"name": name, "entity_type": "npc"}
    if dialogue:
        e["dialogue_lines"] = {"greeting": ["Hello, traveler."]}
    return e


def _enemy(name: str) -> dict:
    return {"name": name, "entity_type": "enemy"}


def _enter_trigger(reaction_type: str = "AlertGamemaster") -> dict:
    return {
        "event_type": "ENTER_TILE",
        "condition": {"type": "AlwaysTrue"},
        "reaction": {"type": reaction_type, "args": {}},
    }


# ── Override ───────────────────────────────────────────────────────────


def test_explicit_override_wins_over_heuristic():
    tile = _tile(tile_type=BOSS, entities=[_enemy("Goblin"), _enemy("Goblin")])
    assert classify_tile(tile) == BOSS


def test_invalid_override_is_ignored():
    tile = _tile(tile_type="totally_wrong_value")
    assert classify_tile(tile) == TRANSIT


# ── NARRATIVE ──────────────────────────────────────────────────────────


def test_single_dialogue_npc_is_narrative():
    tile = _tile(entities=[_npc("Brenna")])
    assert classify_tile(tile) == NARRATIVE


def test_multiple_npcs_is_narrative():
    tile = _tile(entities=[_npc("Brenna"), _npc("Old Torvald")])
    assert classify_tile(tile) == NARRATIVE


def test_npc_without_dialogue_is_not_narrative():
    tile = _tile(entities=[_npc("Silent Bob", dialogue=False)])
    assert classify_tile(tile) != NARRATIVE


def test_dialogue_as_list_counts_as_narrative():
    npc = {"name": "Brenna", "entity_type": "npc",
           "dialogue_lines": ["Welcome."]}
    assert classify_tile(_tile(entities=[npc])) == NARRATIVE


def test_npc_with_enemies_still_narrative():
    """A tavern with a fight brewing is still a narrative scene."""
    tile = _tile(
        entities=[_npc("Brenna"), _enemy("Goblin")],
    )
    assert classify_tile(tile) == NARRATIVE


# ── RIDDLE ─────────────────────────────────────────────────────────────


def test_enter_trigger_without_enemies_is_riddle():
    tile = _tile(triggers=[_enter_trigger("AlertGamemaster")])
    assert classify_tile(tile) == RIDDLE


def test_damage_trigger_does_not_count_as_riddle():
    tile = _tile(triggers=[_enter_trigger("ApplyDamage")])
    assert classify_tile(tile) == TRANSIT


def test_enter_trigger_with_enemies_is_not_riddle():
    tile = _tile(
        triggers=[_enter_trigger("AlertGamemaster")],
        entities=[_enemy("Goblin"), _enemy("Goblin")],
    )
    assert classify_tile(tile) == PACK


# ── BOSS ───────────────────────────────────────────────────────────────


def test_single_unique_named_enemy_is_boss():
    tile = _tile(entities=[_enemy("Grishak the Foul")])
    assert classify_tile(tile) == BOSS


def test_two_unique_named_enemies_is_boss():
    tile = _tile(entities=[
        _enemy("Grishak the Foul"),
        _enemy("Ashen Queen"),
    ])
    assert classify_tile(tile) == BOSS


def test_generic_single_enemy_is_pack_not_boss():
    """A lone Goblin is still a pack-style classification because the
    name is generic (not a distinct character)."""
    assert classify_tile(_tile(entities=[_enemy("Goblin")])) == PACK


def test_two_generic_enemies_is_pack():
    tile = _tile(entities=[_enemy("Wolf"), _enemy("Dire Wolf")])
    assert classify_tile(tile) == PACK


# ── PACK ───────────────────────────────────────────────────────────────


def test_three_plus_enemies_is_pack():
    tile = _tile(entities=[_enemy("Grunt"), _enemy("Thug"), _enemy("Raider")])
    assert classify_tile(tile) == PACK


def test_repeated_enemy_names_is_pack():
    tile = _tile(entities=[_enemy("Goblin"), _enemy("Goblin")])
    assert classify_tile(tile) == PACK


def test_many_same_enemies_is_pack():
    tile = _tile(entities=[_enemy("Goblin")] * 5)
    assert classify_tile(tile) == PACK


# ── TRANSIT ────────────────────────────────────────────────────────────


def test_empty_tile_is_transit():
    assert classify_tile(_tile()) == TRANSIT


def test_damage_trigger_only_is_transit():
    tile = _tile(triggers=[_enter_trigger("ApplyDamage")])
    assert classify_tile(tile) == TRANSIT


def test_decorative_tile_with_note_is_transit():
    tile = _tile(note="A windswept ridge", user_label="Cliff Edge")
    assert classify_tile(tile) == TRANSIT


# ── find_pack_lead ─────────────────────────────────────────────────────


def test_pack_lead_finds_named_among_generics():
    tile = _tile(entities=[
        _enemy("Goblin"),
        _enemy("Goblin"),
        _enemy("Goblin"),
        _enemy("Grishak the Foul"),
    ])
    lead = find_pack_lead(tile)
    assert lead is not None
    assert lead["name"] == "Grishak the Foul"


def test_pack_lead_none_when_all_generic():
    tile = _tile(entities=[_enemy("Goblin")] * 4)
    assert find_pack_lead(tile) is None


def test_pack_lead_none_when_all_distinct():
    """All non-generic enemies means nobody stands out as a 'lead'."""
    tile = _tile(entities=[
        _enemy("Grishak the Foul"),
        _enemy("Ashen Queen"),
    ])
    assert find_pack_lead(tile) is None


def test_pack_lead_requires_multiple_enemies():
    tile = _tile(entities=[_enemy("Grishak the Foul")])
    assert find_pack_lead(tile) is None

"""Unit tests for per-tile-type prompt builders.

Covers every builder in :mod:`tools.tile_prompt_builders`:
- narrative builder lists NPCs and pulls biome silhouettes/mood
- event builder focuses on trigger-derived focal object
- boss builder highlights the named enemy
- pack builder uses generic group name + optional lead overlay
- transit builder stays light
- deterministic lexicon sampling (same tile -> same phrases across runs)
- end-to-end dispatch via ``build_tile_prompt``
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent.parent.parent / "tools"),
)

from tile_prompt_builders import (  # noqa: E402
    build_narrative_phrases,
    build_event_phrases,
    build_boss_phrases,
    build_pack_phrases,
    build_transit_phrases,
    _deterministic_indices,
    _entity_descriptor,
    _generic_group_name,
)
from tile_background_generator import build_tile_prompt  # noqa: E402


_LEXICON = {
    "dark_forest": {
        "palette": "mossy green, slate, muted amber",
        "mood": "hushed, damp, ancient",
        "silhouettes": [
            "a lean wolf with glowing eyes",
            "a weathered druid in moss-stained robes",
            "a drifting will-o-wisp",
        ],
        "landmarks": [
            "a crumbling stone obelisk",
            "a rusted iron lantern hanging from a branch",
        ],
    },
    "scorched_sands": {
        "palette": "bone white, copper red, dusk violet",
        "mood": "vast, pitiless",
        "silhouettes": ["a vulture circling above a ruin"],
        "landmarks": ["a toppled sandstone obelisk"],
    },
}


def _tile(**kwargs) -> dict:
    base = {
        "position": [5, 5],
        "terrain": "GRASS",
        "entities": [],
        "triggers": [],
        "background_image": "assets/backgrounds/dark_forest.png",
    }
    base.update(kwargs)
    return base


# ── Narrative ──────────────────────────────────────────────────────────


def test_narrative_builder_foregrounds_first_npc():
    """Only the first NPC is a detailed subject; the rest become a blur."""
    tile = _tile(
        narrator_intro="A crackling hearth casts warm light across the tavern",
        entities=[
            {"name": "Brenna", "entity_type": "npc",
             "dialogue_lines": {"greet": ["Hi"]}},
            {"name": "Old Torvald", "entity_type": "npc",
             "dialogue_lines": {"greet": ["Ho"]}},
        ],
    )
    rp = build_narrative_phrases(tile, _LEXICON, "dark forest")
    assert "dark forest" in rp.base
    assert "crackling hearth" in rp.base
    assert "Brenna" in rp.center
    assert "central figure" in rp.center
    assert "Old Torvald" not in rp.center
    assert "shadowy companions" in rp.center


def test_narrative_builder_single_npc_no_companions_phrase():
    """A tile with only one NPC shouldn't mention shadowy companions."""
    tile = _tile(
        entities=[
            {"name": "Brenna", "entity_type": "npc",
             "dialogue_lines": {"greet": ["Hi"]}},
        ],
    )
    rp = build_narrative_phrases(tile, _LEXICON, "")
    assert "Brenna" in rp.center
    assert "central figure" in rp.center
    assert "shadowy companions" not in rp.center


def test_narrative_builder_includes_palette_and_mood():
    tile = _tile(
        entities=[
            {"name": "Brenna", "entity_type": "npc",
             "dialogue_lines": {"greet": ["Hi"]}},
        ],
    )
    rp = build_narrative_phrases(tile, _LEXICON, "dark forest")
    assert "mossy green" in rp.base
    assert "hushed" in rp.base


def test_narrative_caps_to_single_foreground_npc():
    """A tavern with 8 NPCs still produces only one detailed subject."""
    npcs = [
        {"name": f"NPC {i}", "entity_type": "npc",
         "dialogue_lines": {"greet": ["hi"]}}
        for i in range(8)
    ]
    tile = _tile(entities=npcs)
    rp = build_narrative_phrases(tile, _LEXICON, "")
    assert "NPC 0" in rp.center
    assert "NPC 1" not in rp.center
    assert "shadowy companions" in rp.center


# ── Event ──────────────────────────────────────────────────────────────


def test_event_builder_uses_narrator_when_present():
    tile = _tile(
        narrator_intro="A pedestal glows in the centre of the clearing",
        triggers=[{"event_type": "ENTER_TILE", "label": "rune_puzzle",
                   "reaction": {"type": "AlertGamemaster"}}],
    )
    phrases = build_event_phrases(tile, _LEXICON, "dark forest")
    joined = ", ".join(phrases)
    assert "pedestal glows" in joined


def test_event_builder_falls_back_to_trigger_label():
    tile = _tile(
        triggers=[{"event_type": "ENTER_TILE", "label": "rune_puzzle",
                   "reaction": {"type": "AlertGamemaster"}}],
    )
    phrases = build_event_phrases(tile, _LEXICON, "")
    joined = ", ".join(phrases)
    assert "rune puzzle" in joined


def test_event_builder_minimal_npc_mention():
    """Event tiles should not clutter with NPC lists."""
    tile = _tile(
        narrator_intro="A glowing rune on the floor",
        entities=[{"name": "Wandering Scholar", "entity_type": "npc",
                   "dialogue_lines": {"greet": ["hi"]}}],
        triggers=[{"event_type": "ENTER_TILE", "label": "rune",
                   "reaction": {"type": "AlertGamemaster"}}],
    )
    phrases = build_event_phrases(tile, _LEXICON, "")
    joined = ", ".join(phrases)
    assert "Wandering Scholar" not in joined


# ── Boss ───────────────────────────────────────────────────────────────


def test_boss_builder_names_lead_enemy():
    tile = _tile(
        narrator_intro="The throne room falls silent as you enter",
        entities=[{"name": "Grishak the Foul", "entity_type": "enemy"}],
    )
    rp = build_boss_phrases(tile, _LEXICON, "dark forest")
    assert "Grishak the Foul" in rp.center
    assert "towering presence" in rp.center


def test_boss_builder_demotes_second_boss_to_silhouette():
    """Two bosses on one tile: first is detailed, second is a flanking blur."""
    tile = _tile(
        entities=[
            {"name": "Ashen Queen", "entity_type": "enemy"},
            {"name": "Ironjaw", "entity_type": "enemy"},
        ],
    )
    rp = build_boss_phrases(tile, _LEXICON, "")
    assert "Ashen Queen" in rp.center
    assert "full body visible" in rp.center
    assert "Ironjaw" not in rp.center
    assert "flank" in rp.center


# ── Pack ───────────────────────────────────────────────────────────────


def test_pack_builder_uses_generic_plural():
    tile = _tile(
        entities=[
            {"name": "Goblin", "entity_type": "enemy"},
            {"name": "Goblin", "entity_type": "enemy"},
            {"name": "Goblin", "entity_type": "enemy"},
        ],
    )
    rp = build_pack_phrases(tile, _LEXICON, "dark forest")
    assert "goblins" in rp.center


def test_pack_builder_foregrounds_lead_when_present():
    """A pack with a distinguished lead: lead is the only detailed subject,
    generic members become vague distant shapes."""
    tile = _tile(
        entities=[
            {"name": "Goblin", "entity_type": "enemy"},
            {"name": "Goblin", "entity_type": "enemy"},
            {"name": "Goblin", "entity_type": "enemy"},
            {"name": "Grishak the Foul", "entity_type": "enemy"},
        ],
    )
    rp = build_pack_phrases(tile, _LEXICON, "")
    assert "Grishak the Foul" in rp.center
    assert "central figure" in rp.center
    assert "lesser shapes" in rp.center


def test_pack_builder_no_lead_when_all_generic():
    tile = _tile(
        entities=[
            {"name": "Goblin", "entity_type": "enemy"},
            {"name": "Goblin", "entity_type": "enemy"},
        ],
    )
    rp = build_pack_phrases(tile, _LEXICON, "")
    assert "indistinct" in rp.center


# ── Transit ────────────────────────────────────────────────────────────


def test_transit_builder_is_minimal():
    tile = _tile()
    phrases = build_transit_phrases(tile, _LEXICON, "dark forest")
    joined = ", ".join(phrases)
    assert "dark forest" in joined
    assert "grass" in joined.lower()


def test_transit_builder_deterministic_per_tile():
    """Same tile position => same lexicon phrase across calls."""
    tile = _tile(position=[7, 13])
    out_a = build_transit_phrases(tile, _LEXICON, "dark forest")
    out_b = build_transit_phrases(tile, _LEXICON, "dark forest")
    assert out_a == out_b


def test_transit_builder_different_tiles_different_phrases():
    """Different positions should sometimes pick different lexicon entries."""
    t1 = _tile(position=[1, 1])
    t2 = _tile(position=[9, 17])
    t3 = _tile(position=[3, 8])
    variants = {
        ", ".join(build_transit_phrases(t, _LEXICON, ""))
        for t in (t1, t2, t3)
    }
    # At least two distinct prompts across three tiles
    assert len(variants) >= 2


# ── Helpers ────────────────────────────────────────────────────────────


def test_deterministic_indices_stable():
    assert _deterministic_indices("abc", 2, 5) == _deterministic_indices("abc", 2, 5)


def test_deterministic_indices_distinct():
    picks = _deterministic_indices("hello", 3, 5)
    assert len(picks) == 3
    assert len(set(picks)) == 3


def test_deterministic_indices_respects_pool_size():
    picks = _deterministic_indices("k", 10, 3)
    assert len(picks) == 3


def test_entity_descriptor_simple_name():
    assert _entity_descriptor({"name": "Goblin"}) == "a goblin"


def test_entity_descriptor_named_character():
    desc = _entity_descriptor({"name": "Grishak the Foul"})
    assert "Grishak the Foul" in desc


def test_entity_descriptor_uses_flavor_if_present():
    desc = _entity_descriptor({
        "name": "Goblin",
        "flavor_description": "a spindly, rag-clad goblin with a crooked dagger",
    })
    assert "spindly" in desc


def test_generic_group_name_singular_to_plural():
    enemies = [{"name": "Wolf"}, {"name": "Wolf"}, {"name": "Wolf"}]
    assert _generic_group_name(enemies) == "wolfs"  # naive pluralizer


def test_generic_group_name_already_plural():
    enemies = [{"name": "Bandits"}, {"name": "Bandits"}]
    assert _generic_group_name(enemies) == "bandits"


# ── End-to-end dispatch via build_tile_prompt ──────────────────────────


def test_build_tile_prompt_routes_narrative():
    from regional_workflow import RegionalPrompt
    tile = _tile(
        entities=[{"name": "Brenna", "entity_type": "npc",
                   "dialogue_lines": {"greet": ["hi"]}}],
    )
    result = build_tile_prompt(tile, biome_hint="dark forest", lexicon=_LEXICON)
    assert isinstance(result, RegionalPrompt)
    assert "Brenna" in result.center
    assert "central figure" in result.center
    assert "masterpiece" in result.base  # style suffix in base


def test_build_tile_prompt_routes_pack_with_lead():
    from regional_workflow import RegionalPrompt
    tile = _tile(
        entities=[
            {"name": "Goblin", "entity_type": "enemy"},
            {"name": "Goblin", "entity_type": "enemy"},
            {"name": "Goblin", "entity_type": "enemy"},
            {"name": "Grishak the Foul", "entity_type": "enemy"},
        ],
    )
    result = build_tile_prompt(tile, biome_hint="dark forest", lexicon=_LEXICON)
    assert isinstance(result, RegionalPrompt)
    assert "Grishak the Foul" in result.center
    assert "central figure" in result.center


def test_build_tile_prompt_transit_has_biome_palette_flavor():
    tile = _tile(position=[12, 7])
    prompt = build_tile_prompt(tile, biome_hint="dark forest", lexicon=_LEXICON)
    # Transit tiles still carry at least one lexicon pick
    has_silhouette = any(
        fragment in prompt for fragment in _LEXICON["dark_forest"]["silhouettes"]
    )
    has_landmark = any(
        fragment in prompt for fragment in _LEXICON["dark_forest"]["landmarks"]
    )
    assert has_silhouette or has_landmark


def test_build_tile_prompt_backward_compat_no_lexicon():
    """Callers that pass no lexicon still get a valid prompt."""
    tile = _tile()
    prompt = build_tile_prompt(tile, biome_hint="dark forest")
    assert "dark forest" in prompt
    assert "grass" in prompt.lower()
    assert "masterpiece" in prompt


def test_build_tile_prompt_honours_explicit_tile_type_override():
    """Override from TRANSIT default to BOSS even with no enemies present."""
    from regional_workflow import RegionalPrompt
    tile = _tile(
        tile_type="boss",
        narrator_intro="A lone figure stands at the end of the hall",
        entities=[{"name": "Ashen Queen", "entity_type": "enemy"}],
    )
    result = build_tile_prompt(tile, biome_hint="dark forest", lexicon=_LEXICON)
    assert isinstance(result, RegionalPrompt)
    assert "Ashen Queen" in result.center
    assert "towering presence" in result.center

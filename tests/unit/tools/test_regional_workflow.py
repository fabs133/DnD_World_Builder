"""Unit tests for regional prompting workflow.

Tests:
- RegionalPrompt dataclass
- Mask PNG generation (correct dimensions, white/black regions)
- Workflow dict structure (node types, connections)
- Builder integration (narrative/boss/pack return RegionalPrompt, transit returns list)
- Prompt dispatcher (build_tile_prompt returns correct type per tile)
"""

from __future__ import annotations

import sys
import struct
import zlib
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent.parent.parent / "tools"),
)

from regional_workflow import (  # noqa: E402
    RegionalPrompt,
    build_regional_workflow,
)
from tile_background_generator import (  # noqa: E402
    build_tile_prompt,
    GenerationTask,
)
from tile_prompt_builders import (  # noqa: E402
    build_narrative_phrases,
    build_boss_phrases,
    build_pack_phrases,
    build_transit_phrases,
    build_event_phrases,
)


# ── Helpers ────────────────────────────────────────────────────────────

def _make_task(**overrides) -> GenerationTask:
    defaults = dict(
        task_type="background",
        entity_name="tile_5_5",
        prompt="test prompt",
        negative="bad quality",
        output_path="assets/tile_backgrounds/test/tile_5_5.png",
        seed=42,
        steps=35,
        cfg=7.0,
        width=1024,
        height=768,
    )
    defaults.update(overrides)
    return GenerationTask(**defaults)


def _make_regional(**overrides) -> RegionalPrompt:
    defaults = dict(
        base="biome, palette, mood, style",
        center="a figure known as Sister Maren as the central figure",
        left="a sagging wooden inn with a creaking sign",
        right="a cat watching from an upstairs window",
        negative="bad anatomy, extra limbs",
    )
    defaults.update(overrides)
    return RegionalPrompt(**defaults)


_LEXICON = {
    "dark_forest": {
        "palette": "mossy green, slate",
        "mood": "hushed, damp",
        "silhouettes": ["a lean wolf with glowing eyes"],
        "landmarks": ["a crumbling stone obelisk"],
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


# ── RegionalPrompt ─────────────────────────────────────────────────────

def test_regional_prompt_fields():
    rp = _make_regional()
    assert rp.center.startswith("a figure known as")
    assert rp.width == 1024
    assert rp.height == 768


# ── Workflow structure ─────────────────────────────────────────────────

def test_workflow_has_required_node_types():
    """The regional workflow must include all expected node classes."""
    task = _make_task()
    rp = _make_regional()
    workflow, mask_files = build_regional_workflow(task, rp)

    node_types = {v["class_type"] for v in workflow.values()}
    required = {
        "CheckpointLoaderSimple",
        "VAELoader",
        "CLIPTextEncode",
        "EmptyLatentImage",
        "KSampler",
        "VAEDecode",
        "SaveImage",
        "SolidMask",
        "MaskComposite",
        "ConditioningSetMask",
        "ConditioningCombine",
    }
    missing = required - node_types
    assert not missing, f"Missing node types: {missing}"


def test_workflow_no_temp_mask_files():
    """Masks are built inside the graph — no temp files should be returned."""
    task = _make_task()
    rp = _make_regional()
    workflow, mask_files = build_regional_workflow(task, rp)
    assert mask_files == []


def test_workflow_ksampler_references_combined_conditioning():
    """KSampler's positive input should point at the final ConditioningCombine."""
    task = _make_task()
    rp = _make_regional()
    workflow, _ = build_regional_workflow(task, rp)
    ksampler = workflow["6"]
    positive_ref = ksampler["inputs"]["positive"]
    # Should reference node 21 (the final combine)
    assert positive_ref == ["21", 0]


def test_workflow_seed_matches_task():
    task = _make_task(seed=12345)
    rp = _make_regional()
    workflow, _ = build_regional_workflow(task, rp)
    assert workflow["6"]["inputs"]["seed"] == 12345


def test_workflow_center_prompt_is_set():
    task = _make_task()
    rp = _make_regional(center="test center prompt")
    workflow, _ = build_regional_workflow(task, rp)
    # Node 9 is the center CLIPTextEncode
    assert workflow["9"]["inputs"]["text"] == "test center prompt"


def test_workflow_left_right_prompts_are_set():
    task = _make_task()
    rp = _make_regional(left="left detail", right="right detail")
    workflow, _ = build_regional_workflow(task, rp)
    assert workflow["12"]["inputs"]["text"] == "left detail"
    assert workflow["15"]["inputs"]["text"] == "right detail"


# ── Builder return types ───────────────────────────────────────────────

def test_narrative_builder_returns_regional_prompt():
    tile = _tile(
        entities=[{"name": "Brenna", "entity_type": "npc",
                   "dialogue_lines": {"greet": ["hi"]}}],
    )
    result = build_narrative_phrases(tile, _LEXICON, "dark forest")
    assert isinstance(result, RegionalPrompt)
    assert "Brenna" in result.center


def test_boss_builder_returns_regional_prompt():
    tile = _tile(
        entities=[{"name": "Grishak the Foul", "entity_type": "enemy"}],
    )
    result = build_boss_phrases(tile, _LEXICON, "dark forest")
    assert isinstance(result, RegionalPrompt)
    assert "Grishak the Foul" in result.center


def test_pack_builder_returns_regional_prompt():
    tile = _tile(
        entities=[
            {"name": "Goblin", "entity_type": "enemy"},
            {"name": "Goblin", "entity_type": "enemy"},
            {"name": "Grishak the Foul", "entity_type": "enemy"},
        ],
    )
    result = build_pack_phrases(tile, _LEXICON, "dark forest")
    assert isinstance(result, RegionalPrompt)
    assert "Grishak the Foul" in result.center


def test_transit_builder_still_returns_list():
    tile = _tile()
    result = build_transit_phrases(tile, _LEXICON, "dark forest")
    assert isinstance(result, list)


def test_event_builder_still_returns_list():
    tile = _tile(
        triggers=[{"event_type": "ENTER_TILE", "label": "puzzle",
                   "reaction": {"type": "AlertGamemaster"}}],
    )
    result = build_event_phrases(tile, _LEXICON, "dark forest")
    assert isinstance(result, list)


# ── Prompt dispatcher ──────────────────────────────────────────────────

def test_build_tile_prompt_returns_regional_for_narrative():
    tile = _tile(
        entities=[{"name": "Brenna", "entity_type": "npc",
                   "dialogue_lines": {"greet": ["hi"]}}],
    )
    result = build_tile_prompt(tile, biome_hint="dark forest", lexicon=_LEXICON)
    assert isinstance(result, RegionalPrompt)
    assert "Brenna" in result.center


def test_build_tile_prompt_returns_str_for_transit():
    tile = _tile()
    result = build_tile_prompt(tile, biome_hint="dark forest", lexicon=_LEXICON)
    assert isinstance(result, str)
    assert "dark forest" in result


def test_build_tile_prompt_adds_edge_structures_to_regional_base():
    tile = _tile(
        entities=[{"name": "Brenna", "entity_type": "npc",
                   "dialogue_lines": {"greet": ["hi"]}}],
        edge_structures=[
            {"name": "Tower", "description": "stone tower",
             "anchor": "right", "propagate": True},
        ],
    )
    result = build_tile_prompt(tile, biome_hint="dark forest", lexicon=_LEXICON)
    assert isinstance(result, RegionalPrompt)
    assert "stone tower on the right edge" in result.base


def test_build_tile_prompt_backward_compat_no_lexicon_flat():
    """No lexicon → transit tiles still produce flat strings."""
    tile = _tile()
    result = build_tile_prompt(tile, biome_hint="dark forest")
    assert isinstance(result, str)

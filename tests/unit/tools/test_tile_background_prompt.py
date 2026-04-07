"""Unit tests for tile background prompt composition.

Exercises :func:`tools.tile_background_generator.build_tile_prompt` across:
- baseline (terrain only)
- narrator intro injection
- own-tile edge structures on left/right
- cross-tile inheritance (left neighbour → current tile's left edge)
- propagate=False suppressing inheritance
- missing neighbours at map edges
- backward compatibility (no tile_index argument)
- TileData round-trip of the new fields
"""

from __future__ import annotations

import sys
from pathlib import Path

# Align with sibling test_comfyui_workflows.py import style.
sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent.parent.parent / "tools"),
)

from tile_background_generator import build_tile_prompt  # noqa: E402
from models.tiles.tile_data import TileData, TerrainType  # noqa: E402


# ── Fixtures ────────────────────────────────────────────────────────────


def _tile(x: int, y: int, **overrides) -> dict:
    base = {"position": [x, y], "terrain": "GRASS"}
    base.update(overrides)
    return base


def _structure(description: str, anchor: str, propagate: bool = True) -> dict:
    return {
        "name": description.split()[0].title(),
        "description": description,
        "anchor": anchor,
        "propagate": propagate,
    }


# ── Baseline & backward compat ──────────────────────────────────────────


def test_baseline_prompt_contains_terrain_and_style():
    prompt = build_tile_prompt(_tile(0, 0))
    assert "grass" in prompt.lower()
    assert "masterpiece" in prompt
    assert "top-down" in prompt


def test_biome_hint_prefixes_prompt():
    prompt = build_tile_prompt(_tile(0, 0), biome_hint="dark fantasy forest")
    assert prompt.startswith("dark fantasy forest")


def test_backward_compat_no_tile_index_matches_legacy_output():
    """Calling without tile_index must produce the same string as before."""
    tile = _tile(5, 5, user_label="Moss Clearing")
    legacy = build_tile_prompt(tile, biome_hint="forest")
    with_index = build_tile_prompt(tile, biome_hint="forest", tile_index=None)
    assert legacy == with_index


# ── Narrator intro ──────────────────────────────────────────────────────


def test_narrator_intro_appears_early_in_prompt():
    narrator = "A moss-carpeted clearing ringed by gnarled oaks"
    tile = _tile(0, 0, narrator_intro=narrator)
    prompt = build_tile_prompt(tile, biome_hint="forest")
    # Narrator should come right after biome hint and before terrain phrase
    assert narrator in prompt
    narrator_idx = prompt.index(narrator)
    terrain_idx = prompt.index("grass")
    biome_idx = prompt.index("forest")
    assert biome_idx < narrator_idx < terrain_idx


def test_empty_narrator_intro_does_not_pollute_prompt():
    tile = _tile(0, 0, narrator_intro="   ")
    prompt = build_tile_prompt(tile)
    assert ", ," not in prompt  # no empty segment


# ── Own edge structures ─────────────────────────────────────────────────


def test_own_right_edge_structure_is_included():
    tile = _tile(
        1, 0,
        edge_structures=[_structure("stone watchtower", "right")],
    )
    prompt = build_tile_prompt(tile)
    assert "stone watchtower on the right edge of the frame" in prompt


def test_own_left_edge_structure_is_included():
    tile = _tile(
        2, 0,
        edge_structures=[_structure("crumbled arch", "left")],
    )
    prompt = build_tile_prompt(tile)
    assert "crumbled arch on the left edge of the frame" in prompt


def test_multiple_own_edge_structures():
    tile = _tile(
        1, 0,
        edge_structures=[
            _structure("stone tower", "left"),
            _structure("ruined wall", "right"),
        ],
    )
    prompt = build_tile_prompt(tile)
    assert "stone tower on the left edge" in prompt
    assert "ruined wall on the right edge" in prompt


def test_edge_structure_missing_description_is_skipped():
    tile = _tile(
        1, 0,
        edge_structures=[{"anchor": "left"}, _structure("tower", "right")],
    )
    prompt = build_tile_prompt(tile)
    assert "tower on the right edge" in prompt
    # The malformed entry should not produce a dangling fragment
    assert "on the left edge" not in prompt


def test_edge_structure_invalid_anchor_is_skipped():
    tile = _tile(
        1, 0,
        edge_structures=[_structure("tower", "top")],
    )
    prompt = build_tile_prompt(tile)
    assert "tower" not in prompt  # silently dropped


# ── Cross-tile inheritance ──────────────────────────────────────────────


def test_inherits_from_left_neighbour_right_edge():
    """Tile (1,0)'s right edge has a tower → (2,0) should show it on its left."""
    left = _tile(1, 0, edge_structures=[_structure("stone tower", "right")])
    centre = _tile(2, 0)
    index = {(1, 0): left, (2, 0): centre}

    prompt = build_tile_prompt(centre, tile_index=index)
    assert "continuation of stone tower entering from the left edge" in prompt


def test_inherits_from_right_neighbour_left_edge():
    """Tile (3,0)'s left edge has an arch → (2,0) should show it on its right."""
    centre = _tile(2, 0)
    right = _tile(3, 0, edge_structures=[_structure("crumbled arch", "left")])
    index = {(2, 0): centre, (3, 0): right}

    prompt = build_tile_prompt(centre, tile_index=index)
    assert "continuation of crumbled arch entering from the right edge" in prompt


def test_inherits_from_both_neighbours():
    left = _tile(1, 0, edge_structures=[_structure("tall tower", "right")])
    centre = _tile(2, 0)
    right = _tile(3, 0, edge_structures=[_structure("stone arch", "left")])
    index = {(1, 0): left, (2, 0): centre, (3, 0): right}

    prompt = build_tile_prompt(centre, tile_index=index)
    assert "continuation of tall tower entering from the left edge" in prompt
    assert "continuation of stone arch entering from the right edge" in prompt


def test_propagate_false_suppresses_inheritance():
    left = _tile(
        1, 0,
        edge_structures=[_structure("decorative statue", "right", propagate=False)],
    )
    centre = _tile(2, 0)
    index = {(1, 0): left, (2, 0): centre}

    prompt = build_tile_prompt(centre, tile_index=index)
    assert "continuation of decorative statue" not in prompt


def test_missing_neighbour_does_not_crash():
    """Tiles at the map edge have no neighbour on one side."""
    centre = _tile(0, 0)  # leftmost column
    index = {(0, 0): centre}
    prompt = build_tile_prompt(centre, tile_index=index)
    # No structures, just baseline content
    assert "grass" in prompt.lower()


def test_own_and_inherited_structures_coexist():
    left = _tile(1, 0, edge_structures=[_structure("watchtower", "right")])
    centre = _tile(
        2, 0,
        edge_structures=[_structure("crumbled arch", "left")],
    )
    index = {(1, 0): left, (2, 0): centre}

    prompt = build_tile_prompt(centre, tile_index=index)
    # Own structure appears on its natural edge
    assert "crumbled arch on the left edge of the frame" in prompt
    # Inherited structure appears as continuation
    assert "continuation of watchtower entering from the left edge" in prompt


def test_inheritance_only_considers_neighbour_matching_anchor():
    """A left-anchored structure on the left neighbour does NOT propagate
    to the current tile — it propagates to the left neighbour's own left
    neighbour."""
    left = _tile(1, 0, edge_structures=[_structure("tower", "left")])
    centre = _tile(2, 0)
    index = {(1, 0): left, (2, 0): centre}

    prompt = build_tile_prompt(centre, tile_index=index)
    assert "continuation of tower" not in prompt


# ── Position parsing ────────────────────────────────────────────────────


def test_tile_without_position_skips_inheritance():
    tile = {"terrain": "GRASS"}  # no position
    index = {(0, 0): {"position": [0, 0], "edge_structures": []}}
    # Must not raise
    prompt = build_tile_prompt(tile, tile_index=index)
    assert "grass" in prompt.lower()


# ── TileData round-trip ─────────────────────────────────────────────────


def test_tiledata_roundtrip_with_new_fields():
    td = TileData(
        tile_id="t1",
        position=(5, 3),
        terrain=TerrainType.GRASS,
        narrator_intro="A mossy clearing beneath ancient oaks",
        edge_structures=[
            {"name": "Tower", "description": "stone tower",
             "anchor": "right", "propagate": True},
        ],
    )
    data = td.to_dict()
    assert data["narrator_intro"] == "A mossy clearing beneath ancient oaks"
    assert data["edge_structures"][0]["description"] == "stone tower"

    restored = TileData.from_dict(data)
    assert restored.narrator_intro == td.narrator_intro
    assert restored.edge_structures == td.edge_structures


def test_tiledata_roundtrip_omits_empty_new_fields():
    """Existing scenarios must round-trip without spurious keys."""
    td = TileData(
        tile_id="t1",
        position=(0, 0),
        terrain=TerrainType.GRASS,
    )
    data = td.to_dict()
    assert "narrator_intro" not in data
    assert "edge_structures" not in data

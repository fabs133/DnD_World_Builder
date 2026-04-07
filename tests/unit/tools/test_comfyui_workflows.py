"""Tests for ComfyUI workflow builders — verify structure, not generation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "tools"))

from comfyui_batch_generator import (
    GenerationTask,
    _build_txt2img_workflow,
    _build_seamless_tile_workflow,
    _build_layerdiffuse_item_workflow,
    DEFAULT_CHECKPOINT,
    DEFAULT_VAE,
)


def _make_task(**overrides):
    defaults = dict(
        task_type="terrain",
        entity_name="stone_floor",
        prompt="dungeon stone floor",
        negative="bad quality",
        output_path="assets/terrain/stone.png",
        seed=42,
    )
    defaults.update(overrides)
    return GenerationTask(**defaults)


class TestSeamlessTileWorkflow:
    def test_contains_seamless_tile_node(self):
        wf = _build_seamless_tile_workflow(_make_task())
        node_types = {n["class_type"] for n in wf.values()}
        assert "SeamlessTile" in node_types

    def test_ksampler_uses_seamless_model(self):
        wf = _build_seamless_tile_workflow(_make_task())
        ksampler = [n for n in wf.values() if n["class_type"] == "KSampler"][0]
        model_ref = ksampler["inputs"]["model"]
        seamless_node_id = [k for k, v in wf.items() if v["class_type"] == "SeamlessTile"][0]
        assert model_ref[0] == seamless_node_id

    def test_uses_circular_vae_decode(self):
        wf = _build_seamless_tile_workflow(_make_task())
        node_types = {n["class_type"] for n in wf.values()}
        assert "CircularVAEDecode" in node_types
        assert "VAEDecode" not in node_types

    def test_has_save_node(self):
        wf = _build_seamless_tile_workflow(_make_task())
        save_nodes = [n for n in wf.values() if n["class_type"] == "SaveImage"]
        assert len(save_nodes) == 1

    def test_seed_passthrough(self):
        wf = _build_seamless_tile_workflow(_make_task(seed=12345))
        ksampler = [n for n in wf.values() if n["class_type"] == "KSampler"][0]
        assert ksampler["inputs"]["seed"] == 12345


class TestLayerDiffuseItemWorkflow:
    def test_contains_layer_diffuse_nodes(self):
        wf = _build_layerdiffuse_item_workflow(_make_task(task_type="item"))
        node_types = {n["class_type"] for n in wf.values()}
        assert "LayeredDiffusionApply" in node_types
        assert "LayeredDiffusionDecode" in node_types

    def test_ksampler_uses_patched_model(self):
        wf = _build_layerdiffuse_item_workflow(_make_task(task_type="item"))
        ksampler = [n for n in wf.values() if n["class_type"] == "KSampler"][0]
        model_ref = ksampler["inputs"]["model"]
        ld_node_id = [k for k, v in wf.items() if v["class_type"] == "LayeredDiffusionApply"][0]
        assert model_ref[0] == ld_node_id

    def test_has_both_vae_decode_and_layer_decode(self):
        wf = _build_layerdiffuse_item_workflow(_make_task(task_type="item"))
        node_types = {n["class_type"] for n in wf.values()}
        assert "VAEDecode" in node_types
        assert "LayeredDiffusionDecode" in node_types

    def test_save_uses_layer_decode_output(self):
        wf = _build_layerdiffuse_item_workflow(_make_task(task_type="item"))
        save = [n for n in wf.values() if n["class_type"] == "SaveImage"][0]
        ld_decode_id = [k for k, v in wf.items() if v["class_type"] == "LayeredDiffusionDecode"][0]
        assert save["inputs"]["images"][0] == ld_decode_id


class TestWorkflowRouting:
    def test_txt2img_has_no_seamless_nodes(self):
        wf = _build_txt2img_workflow(_make_task(task_type="portrait_base"))
        node_types = {n["class_type"] for n in wf.values()}
        assert "SeamlessTile" not in node_types
        assert "LayeredDiffusionApply" not in node_types

    def test_terrain_vs_portrait_different_structure(self):
        portrait_wf = _build_txt2img_workflow(_make_task(task_type="portrait_base"))
        terrain_wf = _build_seamless_tile_workflow(_make_task(task_type="terrain"))
        portrait_types = {n["class_type"] for n in portrait_wf.values()}
        terrain_types = {n["class_type"] for n in terrain_wf.values()}
        assert portrait_types != terrain_types

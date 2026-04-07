"""Regional prompting workflow for ComfyUI.

Builds a multi-region conditioning workflow so each visual element
(NPC, landmark, atmosphere) gets its own spatial mask. The model can
only attend to each element's tokens within its mask region, which
prevents feature merging (e.g., cat-headed NPCs).

Masks are built entirely inside the ComfyUI node graph using
``SolidMask`` + ``MaskComposite`` — no temp files needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from tools.comfyui_batch_generator import GenerationTask
except ImportError:  # pragma: no cover
    from comfyui_batch_generator import GenerationTask  # type: ignore


# ── RegionalPrompt dataclass ──────────────────────────────────────────


@dataclass
class RegionalPrompt:
    """Structured prompt with spatially separated regions.

    Each field feeds a distinct ``ConditioningSetMask`` node so cross-
    attention merging between elements becomes impossible.
    """
    base: str           # whole-image: palette, mood, biome, style suffix
    center: str         # primary subject (NPC / boss / pack lead)
    left: str           # left-third detail (landmark or silhouette)
    right: str          # right-third detail (silhouette or atmosphere)
    negative: str       # anatomy-focused negative for all regions

    # Rendering parameters (set by the generator; builders leave defaults)
    width: int = 1024
    height: int = 768


# ── Region layout constants ───────────────────────────────────────────

# 3-column layout for people-tiles (expressed as fractions of image width).
# Minimal overlap (5%) to avoid object-scale conflicts between regions.
_CENTER = (0.20, 0.80)   # 60% of width — the main subject
_LEFT   = (0.00, 0.25)   # 25% of width — atmospheric scene-setting
_RIGHT  = (0.75, 1.00)   # 25% of width — atmospheric scene-setting

def _get_regional_strengths() -> tuple[float, float, float]:
    """Read regional conditioning strengths from the active model profile."""
    try:
        from tools.model_profile import get_active_profile
    except ImportError:  # pragma: no cover
        from model_profile import get_active_profile  # type: ignore
    p = get_active_profile()
    return p.regional_center_strength, p.regional_side_strength, p.regional_base_strength


# ── Workflow builder ──────────────────────────────────────────────────


def _mask_nodes(
    node_id_base: int,
    img_width: int,
    img_height: int,
    x_start_pct: float,
    x_end_pct: float,
) -> dict[str, dict]:
    """Build SolidMask + MaskComposite nodes for a rectangular region.

    Returns a dict of ``{node_id_str: node_dict}`` with two nodes:
    - ``{base}`` : SolidMask for the white region stamp
    - ``{base+1}`` : MaskComposite that pastes it onto a black canvas

    The caller must also create the black canvas node separately (shared
    across all regions).
    """
    x0 = int(img_width * x_start_pct)
    region_w = int(img_width * x_end_pct) - x0

    stamp_id = str(node_id_base)
    comp_id = str(node_id_base + 1)

    return {
        # White stamp sized to the region
        stamp_id: {
            "class_type": "SolidMask",
            "inputs": {
                "value": 1.0,
                "width": region_w,
                "height": img_height,
            },
        },
        # Composite the stamp onto the shared black canvas
        comp_id: {
            "class_type": "MaskComposite",
            "inputs": {
                "destination": ["50", 0],   # shared black canvas (node 50)
                "source": [stamp_id, 0],
                "x": x0,
                "y": 0,
                "operation": "add",
            },
        },
    }


def build_regional_workflow(
    task: GenerationTask,
    regional: RegionalPrompt,
) -> tuple[dict, list[str]]:
    """Build a ComfyUI workflow with regional conditioning.

    Returns ``(workflow_dict, mask_filenames)`` — ``mask_filenames`` is
    always an empty list since masks are now built inside the graph.
    """
    try:
        from tools.model_profile import get_active_profile
    except ImportError:  # pragma: no cover
        from model_profile import get_active_profile  # type: ignore
    profile = get_active_profile()

    w, h = regional.width, regional.height
    center_str, side_str, base_str = _get_regional_strengths()

    # Build mask node groups (each produces 2 nodes)
    center_mask_nodes = _mask_nodes(60, w, h, *_CENTER)
    left_mask_nodes = _mask_nodes(62, w, h, *_LEFT)
    right_mask_nodes = _mask_nodes(64, w, h, *_RIGHT)

    workflow: dict[str, Any] = {
        # ── Shared ──────────────────────────────────────────
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": task.checkpoint},
        },
        "2": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": task.vae},
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": regional.negative,
                "clip": ["1", 1],
            },
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": w,
                "height": h,
                "batch_size": 1,
            },
        },

        # ── Shared black canvas for MaskComposite destinations ──
        "50": {
            "class_type": "SolidMask",
            "inputs": {
                "value": 0.0,
                "width": w,
                "height": h,
            },
        },

        # ── Full white mask for base conditioning ───────────
        "51": {
            "class_type": "SolidMask",
            "inputs": {
                "value": 1.0,
                "width": w,
                "height": h,
            },
        },

        # ── Base conditioning (whole image, low weight) ─────
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": regional.base,
                "clip": ["1", 1],
            },
        },
        "31": {
            "class_type": "ConditioningSetMask",
            "inputs": {
                "conditioning": ["3", 0],
                "mask": ["51", 0],        # full white mask
                "strength": base_str,
                "set_cond_area": "default",
            },
        },

        # ── Center region (primary subject) ─────────────────
        "9": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": regional.center,
                "clip": ["1", 1],
            },
        },
        "11": {
            "class_type": "ConditioningSetMask",
            "inputs": {
                "conditioning": ["9", 0],
                "mask": ["61", 0],        # center composite mask
                "strength": center_str,
                "set_cond_area": "default",
            },
        },

        # ── Left region ─────────────────────────────────────
        "12": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": regional.left,
                "clip": ["1", 1],
            },
        },
        "14": {
            "class_type": "ConditioningSetMask",
            "inputs": {
                "conditioning": ["12", 0],
                "mask": ["63", 0],        # left composite mask
                "strength": side_str,
                "set_cond_area": "default",
            },
        },

        # ── Right region ────────────────────────────────────
        "15": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": regional.right,
                "clip": ["1", 1],
            },
        },
        "17": {
            "class_type": "ConditioningSetMask",
            "inputs": {
                "conditioning": ["15", 0],
                "mask": ["65", 0],        # right composite mask
                "strength": side_str,
                "set_cond_area": "default",
            },
        },

        # ── Combine all regions ─────────────────────────────
        "19": {
            "class_type": "ConditioningCombine",
            "inputs": {
                "conditioning_1": ["11", 0],   # center
                "conditioning_2": ["14", 0],   # left
            },
        },
        "20": {
            "class_type": "ConditioningCombine",
            "inputs": {
                "conditioning_1": ["19", 0],   # center+left
                "conditioning_2": ["17", 0],   # right
            },
        },
        "21": {
            "class_type": "ConditioningCombine",
            "inputs": {
                "conditioning_1": ["20", 0],   # center+left+right
                "conditioning_2": ["31", 0],   # base
            },
        },

        # ── Sampler + decode + save ─────────────────────────
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["21", 0],       # combined regional conditioning
                "negative": ["4", 0],
                "latent_image": ["5", 0],
                "seed": task.seed,
                "steps": task.steps,
                "cfg": task.cfg,
                "sampler_name": profile.sampler,
                "scheduler": profile.scheduler,
                "denoise": 1.0,
            },
        },
        "7": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["6", 0],
                "vae": ["2", 0],
            },
        },
        "8": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["7", 0],
                "filename_prefix": task.filename_prefix,
            },
        },
    }

    # Merge the mask node groups into the workflow
    workflow.update(center_mask_nodes)
    workflow.update(left_mask_nodes)
    workflow.update(right_mask_nodes)

    # No temp files — masks are built inside the graph
    return workflow, []


def cleanup_masks(filenames: list[str]) -> None:
    """No-op — masks are now built inside the ComfyUI graph.

    Kept for backward compatibility with callers that still call this
    after generation.
    """
    pass

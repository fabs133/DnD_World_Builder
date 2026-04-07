#!/usr/bin/env python3
"""ComfyUI Batch Asset Generator for DnD World Builder.

Reads biome YAML schemas (and world YAML files), extracts all assets
marked as ``status: pending``, builds ComfyUI workflow prompts, and
submits them to the ComfyUI API for generation.

Usage:
    python comfyui_batch_generator.py <yaml_file_or_dir> [options]

Examples:
    # Generate all pending assets from one biome
    python comfyui_batch_generator.py biome_dark_forest.yaml

    # Generate all pending assets from a world file + all its biomes
    python comfyui_batch_generator.py world_shattered_realms.yaml

    # Only portraits
    python comfyui_batch_generator.py biome_dark_forest.yaml --only portraits

    # Only items (with transparent backgrounds via LayerDiffuse)
    python comfyui_batch_generator.py biome_dark_forest.yaml --only items

    # Only tileable terrain textures (via SeamlessTile)
    python comfyui_batch_generator.py biome_dark_forest.yaml --only tiles

    # Dry run — show what would be generated without submitting
    python comfyui_batch_generator.py biome_dark_forest.yaml --dry-run

    # Scan and report status
    python comfyui_batch_generator.py biome_dark_forest.yaml --status
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import urllib.request
import urllib.error
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


# ─── Configuration ──────────────────────────────────────────────────

COMFYUI_API = os.environ.get("COMFYUI_API", "http://127.0.0.1:8000")
OUTPUT_DIR = Path(os.environ.get(
    "COMFYUI_OUTPUT_DIR",
    r"D:\fbrmp\Documents\output",
))
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ASSETS = PROJECT_ROOT / "assets"

# Default generation settings
DEFAULT_CHECKPOINT = "dreamshaper_8.safetensors"
DEFAULT_VAE = "vae-ft-mse-840000-ema-pruned.safetensors"
DEFAULT_TEXTURE_CHECKPOINT = "Realistic_Vision_V5.1_fp16-no-ema.safetensors"
DEFAULT_UPSCALER = "4x-UltraSharp.pth"

NEGATIVE_PORTRAIT = (
    "full body, legs, feet, standing, action pose, weapon in hand, "
    "holding weapon, full figure, below waist, "
    "modern clothing, anime, chibi, blurry, deformed, extra fingers, "
    "bad anatomy, text, watermark, logo, signature, ugly, duplicate, "
    "morbid, mutilated, out of frame, poorly drawn face, mutation, "
    "extra limbs, bad proportions, cloned face, gross proportions, "
    "malformed limbs, missing arms, missing legs, extra arms, "
    "fused fingers, too many fingers, long neck, cropped"
)
NEGATIVE_ITEM = (
    "person, human, figure, character, body, hand, hands, fingers, arm, "
    "face, portrait, armor, clothing, warrior, soldier, holding, wielding, "
    "pedestal, platform, ground, floor, surface, table, stand, base, "
    "3d render, photograph, realistic, photorealistic, "
    "scenery, landscape, background detail, busy background, "
    "colored background, gradient background, "
    "text, watermark, blurry, multiple objects, cropped, out of frame, "
    "crossed, overlapping, pair, two weapons, dual"
)
NEGATIVE_TERRAIN = (
    "person, object, horizon, sky, perspective, 3d, text, watermark, "
    "strong shadows, vignette, depth of field, bokeh, "
    "symmetrical, mirrored, kaleidoscope, repeating pattern, geometric, "
    "fractal, mandala, grid lines, border, frame"
)
NEGATIVE_BACKGROUND = (
    "people, characters, text, watermark, modern, urban, bright cheerful, "
    "cartoon, anime, low quality, blurry"
)


# ─── Data structures ────────────────────────────────────────────────

@dataclass
class GenerationTask:
    """A single image generation task extracted from the schema."""
    task_type: str          # portrait_base, portrait_variant, item, terrain, background
    entity_name: str
    prompt: str
    negative: str
    output_path: str
    seed: int
    steps: int = 30
    cfg: float = 7.0
    width: int = 512
    height: int = 512
    denoise: float = 1.0
    source_image: str = ""  # For img2img variants
    checkpoint: str = DEFAULT_CHECKPOINT
    vae: str = DEFAULT_VAE
    health_state: str = ""  # healthy, wounded, bloodied, critical
    status: str = "pending"

    @property
    def filename_prefix(self) -> str:
        """Generate ComfyUI-friendly filename prefix."""
        name = self.entity_name.lower().replace(" ", "_").replace("'", "")
        if self.health_state:
            return f"{name}_{self.health_state}"
        return name


# ─── Workflow builders ───────────────────────────────────────────────

def _build_txt2img_workflow(task: GenerationTask) -> dict:
    """Build a ComfyUI txt2img workflow for the API."""
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": task.checkpoint},
        },
        "2": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": task.vae},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": task.prompt,
                "clip": ["1", 1],
            },
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": task.negative,
                "clip": ["1", 1],
            },
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": task.width,
                "height": task.height,
                "batch_size": 1,
            },
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["5", 0],
                "seed": task.seed,
                "steps": task.steps,
                "cfg": task.cfg,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
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


def _build_img2img_workflow(task: GenerationTask) -> dict:
    """Build a ComfyUI img2img workflow for health-state variants."""
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": task.checkpoint},
        },
        "2": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": task.vae},
        },
        "3": {
            "class_type": "LoadImage",
            "inputs": {"image": task.source_image},
        },
        "4": {
            "class_type": "VAEEncode",
            "inputs": {
                "pixels": ["3", 0],
                "vae": ["2", 0],
            },
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": task.prompt,
                "clip": ["1", 1],
            },
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": task.negative,
                "clip": ["1", 1],
            },
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["4", 0],
                "seed": task.seed,
                "steps": task.steps,
                "cfg": task.cfg,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": task.denoise,
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["7", 0],
                "vae": ["2", 0],
            },
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["8", 0],
                "filename_prefix": task.filename_prefix,
            },
        },
    }


def _build_seamless_tile_workflow(task: GenerationTask) -> dict:
    """Build a ComfyUI workflow for seamless tileable textures.

    Requires ComfyUI-seamless-tiling custom nodes:
    https://github.com/spinagon/ComfyUI-seamless-tiling

    Uses SeamlessTile node (circular convolution) so edges wrap perfectly,
    and CircularVAEDecode to prevent edge bleeding during decode.
    """
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": task.checkpoint},
        },
        "2": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": task.vae},
        },
        # SeamlessTile modifies the model for circular convolution
        "3": {
            "class_type": "SeamlessTile",
            "inputs": {
                "model": ["1", 0],
                "tiling": "enable",
                "copy_model": "Make a copy",
            },
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": task.prompt,
                "clip": ["1", 1],
            },
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": task.negative,
                "clip": ["1", 1],
            },
        },
        "6": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": task.width,
                "height": task.height,
                "batch_size": 1,
            },
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["3", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["6", 0],
                "seed": task.seed,
                "steps": task.steps,
                "cfg": task.cfg,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
            },
        },
        # CircularVAEDecode prevents edge bleeding during decode
        "8": {
            "class_type": "CircularVAEDecode",
            "inputs": {
                "samples": ["7", 0],
                "vae": ["2", 0],
                "tiling": "enable",
            },
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["8", 0],
                "filename_prefix": task.filename_prefix,
            },
        },
    }


def _build_layerdiffuse_item_workflow(task: GenerationTask) -> dict:
    """Build a ComfyUI workflow for isolated items with transparent backgrounds.

    Requires ComfyUI-layerdiffuse custom nodes:
    https://github.com/huchenlei/ComfyUI-layerdiffuse

    Uses LayerDiffuse Attention Injection to generate the item with a
    latent alpha channel, then LayerDiffuseDecode to extract the RGBA image.
    Output is saved as PNG with transparency.
    """
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": task.checkpoint},
        },
        "2": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": task.vae},
        },
        # LayerDiffuseApply patches the model for transparent generation
        "3": {
            "class_type": "LayeredDiffusionApply",
            "inputs": {
                "model": ["1", 0],
                "config": "SD15, Attention Injection, attn_sharing",
                "weight": 1.0,
            },
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": task.prompt,
                "clip": ["1", 1],
            },
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": task.negative,
                "clip": ["1", 1],
            },
        },
        "6": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": task.width,
                "height": task.height,
                "batch_size": 1,
            },
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["3", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["6", 0],
                "seed": task.seed,
                "steps": task.steps,
                "cfg": task.cfg,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
            },
        },
        # Standard VAE decode (LayerDiffuseDecode needs both samples + images)
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["7", 0],
                "vae": ["2", 0],
            },
        },
        # LayerDiffuseDecode extracts the RGBA image with alpha channel
        "9": {
            "class_type": "LayeredDiffusionDecode",
            "inputs": {
                "samples": ["7", 0],
                "images": ["8", 0],
                "sd_version": "SD15",
                "sub_batch_size": 1,
            },
        },
        "10": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["9", 0],
                "filename_prefix": task.filename_prefix,
            },
        },
    }


# ─── Schema parsing ─────────────────────────────────────────────────

def _name_to_seed(name: str, offset: int = 0) -> int:
    """Deterministic seed from entity name — same name always gets same seed."""
    h = hash(name) & 0x7FFFFFFF  # positive 31-bit int
    return (h + offset) % (2**31)


def _parse_portrait_tasks(
    entity: dict,
    base_prompt_suffix: str = "",
) -> list[GenerationTask]:
    """Extract portrait generation tasks from an entity dict."""
    tasks = []
    portraits = entity.get("portraits", {})
    if not portraits or not portraits.get("needed"):
        return tasks

    name = entity["name"]
    prompt_base = portraits.get("prompt_base", "")
    if not prompt_base:
        return tasks

    style = portraits.get("style", "humanoid")
    # Reinforce bust framing for portrait styles
    framing = ""
    if style in ("humanoid", "creature"):
        framing = ", close up portrait, head and shoulders, upper body only"
    full_prompt = f"{prompt_base.strip()}{framing}, masterpiece, best quality{base_prompt_suffix}"
    base_seed = _name_to_seed(name)

    health_states = portraits.get("health_states", {})

    # Healthy — always txt2img
    healthy = health_states.get("healthy", {})
    if healthy and healthy.get("status", "pending") == "pending":
        tasks.append(GenerationTask(
            task_type="portrait_base",
            entity_name=name,
            prompt=full_prompt,
            negative=NEGATIVE_PORTRAIT,
            output_path=healthy.get("output", ""),
            seed=base_seed,
            steps=30,
            cfg=7.0,
            health_state="healthy",
        ))

    # Wounded / bloodied / critical — img2img from healthy
    denoise_map = {"wounded": 0.40, "bloodied": 0.50, "critical": 0.60}
    for state, default_denoise in denoise_map.items():
        state_data = health_states.get(state, {})
        if not state_data or state_data.get("status", "pending") != "pending":
            continue

        prompt_mod = state_data.get("prompt_mod", "")
        denoise = state_data.get("denoise", default_denoise)

        variant_prompt = (
            f"{prompt_base.strip()}, same character, {prompt_mod}, "
            f"masterpiece, best quality{base_prompt_suffix}"
        )

        healthy_prefix = name.lower().replace(" ", "_").replace("'", "") + "_healthy"
        source = f"{healthy_prefix}_00001_.png"

        variant_negative = (
            NEGATIVE_PORTRAIT
            + ", happy expression, clean pristine, bright cheerful"
            + ", different person, different face, different character, changed identity, wrong outfit"
        )

        tasks.append(GenerationTask(
            task_type="portrait_variant",
            entity_name=name,
            prompt=variant_prompt,
            negative=variant_negative,
            output_path=state_data.get("output", ""),
            seed=base_seed,
            steps=30,
            cfg=7.0,
            denoise=denoise,
            source_image=source,
            health_state=state,
        ))

    return tasks


def _parse_item_tasks(entity: dict) -> list[GenerationTask]:
    """Extract item icon tasks from object-type entities."""
    tasks = []
    portraits = entity.get("portraits", {})
    if not portraits or not portraits.get("needed"):
        return tasks

    if portraits.get("style") != "object":
        return tasks

    name = entity["name"]
    prompt_base = portraits.get("prompt_base", "")
    if not prompt_base:
        return tasks

    healthy = portraits.get("health_states", {}).get("healthy", {})
    if not healthy or healthy.get("status", "pending") != "pending":
        return tasks

    tasks.append(GenerationTask(
        task_type="item",
        entity_name=name,
        prompt=(f"{prompt_base.strip()}, centered, front view, "
                f"transparent background, studio lighting, no shadow, "
                f"sharp focus, masterpiece, best quality"),
        negative=NEGATIVE_ITEM,
        output_path=healthy.get("output", ""),
        seed=_name_to_seed(name, offset=5000),
        steps=25,
        cfg=7.5,
    ))
    return tasks


def _parse_biome_assets(biome: dict) -> list[GenerationTask]:
    """Extract background and terrain tasks from biome header."""
    tasks = []
    assets = biome.get("assets", {})

    bg = assets.get("background", {})
    if bg.get("needed") and bg.get("status", "pending") == "pending":
        prompt = bg.get("prompt", "")
        if prompt:
            tasks.append(GenerationTask(
                task_type="background",
                entity_name=biome.get("name", "background"),
                prompt=f"{prompt.strip()}, masterpiece, best quality",
                negative=NEGATIVE_BACKGROUND,
                output_path=bg.get("output", ""),
                seed=_name_to_seed(biome.get("id", "bg"), offset=9000),
                steps=35,
                cfg=7.5,
                width=768,
                height=512,
            ))

    terrain = assets.get("terrain_texture", {})
    if terrain.get("needed") and terrain.get("status", "pending") == "pending":
        prompt = terrain.get("prompt", "")
        if prompt:
            tasks.append(GenerationTask(
                task_type="terrain",
                entity_name=terrain.get("terrain_type", "texture"),
                prompt=(f"seamless tileable texture, top-down view, "
                        f"{prompt.strip()}, highly detailed surface, "
                        f"masterpiece, best quality"),
                negative=NEGATIVE_TERRAIN,
                output_path=terrain.get("output", ""),
                seed=_name_to_seed(biome.get("id", "terrain"), offset=7000),
                steps=25,
                cfg=7.0,
                checkpoint=DEFAULT_TEXTURE_CHECKPOINT,
            ))

    return tasks


def _parse_zone_backgrounds(zones: list[dict], biome_id: str) -> list[GenerationTask]:
    """Extract zone-level background tasks from zones list."""
    tasks = []
    for zone in zones:
        bg = zone.get("background", {})
        if bg.get("needed") and bg.get("status", "pending") == "pending":
            prompt = bg.get("prompt", "")
            if prompt:
                zone_id = zone.get("id", "zone")
                tasks.append(GenerationTask(
                    task_type="background",
                    entity_name=f"{biome_id}_{zone_id}",
                    prompt=f"{prompt.strip()}, masterpiece, best quality",
                    negative=NEGATIVE_BACKGROUND,
                    output_path=bg.get("output", ""),
                    seed=_name_to_seed(f"{biome_id}_{zone_id}", offset=9500),
                    steps=35,
                    cfg=7.5,
                    width=768,
                    height=512,
                ))
    return tasks


def parse_biome_yaml(filepath: Path) -> list[GenerationTask]:
    """Parse a biome YAML file and extract all pending generation tasks."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    tasks = []

    biome = data.get("biome", {})
    tasks.extend(_parse_biome_assets(biome))

    biome_id = biome.get("id", filepath.stem)
    tasks.extend(_parse_zone_backgrounds(data.get("zones", []), biome_id))

    for entity in data.get("entities", []):
        etype = entity.get("entity_type", "")
        if etype == "object":
            tasks.extend(_parse_item_tasks(entity))
        else:
            tasks.extend(_parse_portrait_tasks(entity))

    return tasks


def parse_world_yaml(filepath: Path) -> list[GenerationTask]:
    """Parse a world YAML file and extract tasks from it + all referenced biomes."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    tasks = []
    base_dir = filepath.parent

    players = data.get("players", {})
    for char in players.get("characters", []):
        tasks.extend(_parse_portrait_tasks(char))

    for item in data.get("shared_items", []):
        if item.get("status", "pending") == "pending":
            prompt = item.get("prompt", "")
            if prompt:
                tasks.append(GenerationTask(
                    task_type="item",
                    entity_name=item["name"],
                    prompt=(f"{prompt.strip()}, centered, front view, "
                            f"transparent background, studio lighting, no shadow, "
                            f"sharp focus, masterpiece, best quality"),
                    negative=NEGATIVE_ITEM,
                    output_path=item.get("output", ""),
                    seed=_name_to_seed(item["name"], offset=5000),
                    steps=25,
                    cfg=7.5,
                ))

    biome_files = data.get("world", {}).get("biome_files", {})
    for biome_id, filename in biome_files.items():
        biome_path = base_dir / filename
        if biome_path.exists():
            print(f"  Loading biome: {biome_id} from {filename}")
            tasks.extend(parse_biome_yaml(biome_path))
        else:
            print(f"  [SKIP] Biome file not found: {filename}")

    return tasks


# ─── ComfyUI API ─────────────────────────────────────────────────────

def submit_prompt(workflow: dict) -> str | None:
    """Submit a workflow to ComfyUI and return the prompt_id."""
    payload = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFYUI_API}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("prompt_id")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"    API Error {e.code}: {body[:300]}")
        return None
    except Exception as e:
        print(f"    Connection error: {e}")
        return None


def wait_for_completion(prompt_id: str, timeout: int = 120) -> dict | None:
    """Poll ComfyUI until the prompt finishes or times out."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(
                f"{COMFYUI_API}/history/{prompt_id}",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                history = json.loads(resp.read().decode("utf-8"))
                if prompt_id in history:
                    return history[prompt_id]
        except Exception:
            pass
        time.sleep(1.0)
    return None


def get_output_images(history_entry: dict) -> list[dict]:
    """Extract output image info from a history entry."""
    images = []
    outputs = history_entry.get("outputs", {})
    for node_id, node_output in outputs.items():
        for img in node_output.get("images", []):
            images.append({
                "filename": img["filename"],
                "subfolder": img.get("subfolder", ""),
                "type": img.get("type", "output"),
            })
    return images


def copy_output_to_project(filename: str, target_path: str) -> bool:
    """Copy a generated image from ComfyUI output to the project assets folder."""
    source = OUTPUT_DIR / filename
    if not source.exists():
        print(f"    [WARN] Output not found: {source}")
        return False

    target = Path(target_path)
    if not target.is_absolute():
        target = PROJECT_ASSETS / target_path.replace("assets/", "", 1)

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


# ─── Main execution ─────────────────────────────────────────────────

def run_batch(
    tasks: list[GenerationTask],
    dry_run: bool = False,
    auto_copy: bool = True,
    pause_between: float = 2.0,
) -> dict:
    """Execute a batch of generation tasks against ComfyUI."""
    base_tasks = [t for t in tasks if t.task_type != "portrait_variant"]
    variant_tasks = [t for t in tasks if t.task_type == "portrait_variant"]

    summary = {"submitted": 0, "completed": 0, "failed": 0, "skipped": 0, "copied": 0}

    print(f"\n{'='*60}")
    print(f"  BATCH GENERATION — {len(tasks)} tasks")
    print(f"  Phase 1: {len(base_tasks)} base images (txt2img)")
    print(f"  Phase 2: {len(variant_tasks)} variants (img2img)")
    print(f"{'='*60}\n")

    if dry_run:
        print("[DRY RUN] Would generate:\n")
        for t in tasks:
            print(f"  [{t.task_type:18s}] {t.entity_name:25s} "
                  f"state={t.health_state or 'n/a':10s} -> {t.output_path}")
        print(f"\nTotal: {len(tasks)} images")
        return summary

    # Phase 1: Base images
    if base_tasks:
        print("── Phase 1: Base images ────────────────────────────────\n")
        _run_task_list(base_tasks, summary, auto_copy, pause_between)

    # Between phases: copy healthy portraits to ComfyUI input folder
    if variant_tasks:
        print("\n── Copying healthy portraits to ComfyUI input/ ─────────\n")
        comfyui_input_dir = OUTPUT_DIR.parent / "input"
        comfyui_input_dir.mkdir(exist_ok=True)

        seen_sources = set()
        for vt in variant_tasks:
            if vt.source_image in seen_sources:
                continue
            seen_sources.add(vt.source_image)
            dest = comfyui_input_dir / vt.source_image
            # Always find the LATEST matching file (highest number suffix)
            prefix = vt.source_image.split("_00001_")[0]
            matches = sorted(OUTPUT_DIR.glob(f"{prefix}_*.png"))
            if matches:
                shutil.copy2(matches[-1], dest)
                print(f"  Copied {matches[-1].name} → input/{vt.source_image}")
            else:
                print(f"  [WARN] Healthy portrait not found for "
                      f"{vt.entity_name}: {vt.source_image}")

        print("\n── Phase 2: Health-state variants ──────────────────────\n")
        _run_task_list(variant_tasks, summary, auto_copy, pause_between)

    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE")
    print(f"  Submitted: {summary['submitted']}")
    print(f"  Completed: {summary['completed']}")
    print(f"  Failed:    {summary['failed']}")
    print(f"  Copied:    {summary['copied']}")
    print(f"{'='*60}\n")

    return summary


def _run_task_list(
    tasks: list[GenerationTask],
    summary: dict,
    auto_copy: bool,
    pause_between: float,
):
    """Run a list of tasks sequentially.

    For portrait variants, chains the output: healthy→wounded→bloodied→critical.
    Each variant uses the previous state's output as its img2img source.
    """
    for i, task in enumerate(tasks, 1):
        print(f"  [{i}/{len(tasks)}] {task.task_type}: {task.entity_name} "
              f"({task.health_state or 'base'})")

        if task.task_type == "portrait_variant":
            workflow = _build_img2img_workflow(task)
        elif task.task_type == "terrain":
            workflow = _build_seamless_tile_workflow(task)
        elif task.task_type == "item":
            # LayerDiffuse (attn_sharing) is incompatible with current
            # ComfyUI desktop; fall back to txt2img with improved prompts.
            # Re-enable when ComfyUI-layerdiffuse updates:
            #   workflow = _build_layerdiffuse_item_workflow(task)
            workflow = _build_txt2img_workflow(task)
        else:
            workflow = _build_txt2img_workflow(task)

        prompt_id = submit_prompt(workflow)
        if not prompt_id:
            print(f"    FAILED to submit")
            summary["failed"] += 1
            continue
        summary["submitted"] += 1
        print(f"    Submitted: {prompt_id[:12]}...")

        result = wait_for_completion(prompt_id, timeout=120)
        if not result:
            print(f"    TIMEOUT — check ComfyUI for errors")
            summary["failed"] += 1
            continue

        status = result.get("status", {})
        if status.get("status_str") == "error":
            msgs = status.get("messages", [])
            error_text = str(msgs)[:200] if msgs else "unknown error"
            print(f"    ERROR: {error_text}")
            summary["failed"] += 1
            continue

        images = get_output_images(result)
        if images:
            filename = images[0]["filename"]
            print(f"    Generated: {filename}")
            summary["completed"] += 1

            if auto_copy and task.output_path:
                if copy_output_to_project(filename, task.output_path):
                    print(f"    Copied → {task.output_path}")
                    summary["copied"] += 1
        else:
            print(f"    No output images found")
            summary["failed"] += 1

        if i < len(tasks):
            time.sleep(pause_between)


def print_status(tasks: list[GenerationTask]):
    """Print a status report of all tasks."""
    print(f"\n{'='*60}")
    print(f"  ASSET STATUS REPORT — {len(tasks)} total tasks")
    print(f"{'='*60}\n")

    by_type: dict[str, list] = {}
    for t in tasks:
        by_type.setdefault(t.task_type, []).append(t)

    for task_type, type_tasks in sorted(by_type.items()):
        pending = sum(1 for t in type_tasks if t.status == "pending")
        done = len(type_tasks) - pending
        print(f"  {task_type:20s}: {len(type_tasks):3d} total | "
              f"{pending:3d} pending | {done:3d} done")

    print(f"\n  {'TOTAL':20s}: {len(tasks):3d} total | "
          f"{sum(1 for t in tasks if t.status == 'pending'):3d} pending")
    print()


# ─── CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Batch generate DnD assets via ComfyUI API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input", type=Path,
        help="YAML file (biome_*.yaml or world_*.yaml) or directory of YAMLs",
    )
    parser.add_argument(
        "--only", choices=["portraits", "items", "terrain", "tiles", "backgrounds", "variants"],
        help="Only generate a specific asset type (tiles is an alias for terrain)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be generated without submitting",
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Print status report and exit",
    )
    parser.add_argument(
        "--no-copy", action="store_true",
        help="Don't auto-copy results to project assets folder",
    )
    parser.add_argument(
        "--pause", type=float, default=2.0,
        help="Seconds between tasks (default: 2.0)",
    )

    args = parser.parse_args()

    input_path = args.input
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)

    print(f"Loading: {input_path}")

    if input_path.is_dir():
        tasks = []
        for yml in sorted(input_path.glob("*.yaml")):
            print(f"  Parsing: {yml.name}")
            if yml.name.startswith("world_"):
                tasks.extend(parse_world_yaml(yml))
            elif yml.name.startswith("biome_"):
                tasks.extend(parse_biome_yaml(yml))
    elif input_path.name.startswith("world_"):
        tasks = parse_world_yaml(input_path)
    else:
        tasks = parse_biome_yaml(input_path)

    type_filter_map = {
        "portraits": ["portrait_base"],
        "variants": ["portrait_variant"],
        "items": ["item"],
        "terrain": ["terrain"],
        "tiles": ["terrain"],
        "backgrounds": ["background"],
    }
    if args.only:
        allowed = type_filter_map.get(args.only, [])
        tasks = [t for t in tasks if t.task_type in allowed]

    if not tasks:
        print("No pending tasks found.")
        sys.exit(0)

    if args.status:
        print_status(tasks)
        sys.exit(0)

    summary = run_batch(
        tasks,
        dry_run=args.dry_run,
        auto_copy=not args.no_copy,
        pause_between=args.pause,
    )

    if summary.get("failed", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Regenerate damaged (double-upscaled) tile backgrounds via ComfyUI txt2img.

Identifies tiles with incorrect resolution, maps them to biome prompts,
generates fresh 768x512 images, then upscales to 1536x1024.

Usage:
    python tools/regenerate_damaged_backgrounds.py --dry-run
    python tools/regenerate_damaged_backgrounds.py
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
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. pip install pyyaml")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

COMFYUI_API = os.environ.get("COMFYUI_API", "http://127.0.0.1:8000")
COMFYUI_INPUT_DIR = Path(os.environ.get("COMFYUI_INPUT_DIR", r"D:\fbrmp\Documents\input"))
COMFYUI_OUTPUT_DIR = Path(os.environ.get("COMFYUI_OUTPUT_DIR", r"D:\fbrmp\Documents\output"))

DEFAULT_CHECKPOINT = "dreamshaper_8.safetensors"
DEFAULT_VAE = "vae-ft-mse-840000-ema-pruned.safetensors"
DEFAULT_UPSCALER = "4x-UltraSharp.pth"
CORRECT_SIZE = (1536, 1024)
ORIGINAL_SIZE = (768, 512)

NEGATIVE = (
    "text, watermark, signature, logo, blurry, ugly, deformed, "
    "modern, photo, selfie, person close-up, face close-up, "
    "anime, cartoon, 3d render, low quality"
)

# Fallback prompts when no biome match found
TERRAIN_PROMPTS = {
    "FLOOR": "medieval stone floor interior, torch-lit dungeon corridor, "
             "ancient stonework, atmospheric fantasy illustration",
    "GRASS": "lush green meadow, medieval countryside, rolling hills, "
             "wildflowers, fantasy landscape painting",
    "FOREST": "dense ancient forest, dappled sunlight through canopy, "
              "mossy trees, fantasy woodland illustration",
    "MOUNTAIN": "rugged mountain path, rocky terrain, alpine vista, "
                "fantasy mountain landscape painting",
    "WATER": "river crossing, stone bridge over stream, reeds and willows, "
             "fantasy waterscape illustration",
    "SAND": "scorched desert sands, ancient ruins half-buried, "
            "heat haze, fantasy desert landscape",
    "SNOW": "frozen tundra, ice-covered ruins, blowing snow, "
            "northern lights, fantasy winter landscape",
    "SWAMP": "murky swamp, twisted dead trees, fog hanging low, "
             "bioluminescent fungi, fantasy marshland",
}


def build_txt2img_workflow(
    prompt: str,
    negative: str = NEGATIVE,
    checkpoint: str = DEFAULT_CHECKPOINT,
    vae: str = DEFAULT_VAE,
    width: int = 768,
    height: int = 512,
    seed: int = -1,
    output_prefix: str = "regen",
) -> dict:
    """ComfyUI workflow: txt2img at specified resolution."""
    import random
    if seed < 0:
        seed = random.randint(0, 2**32 - 1)

    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
                "seed": seed,
                "steps": 25,
                "cfg": 7.0,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": 1.0,
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"images": ["6", 0], "filename_prefix": output_prefix},
        },
    }


def build_upscale_workflow(input_filename: str, output_prefix: str = "upscaled") -> dict:
    """ComfyUI workflow: load image + ESRGAN 4x upscale."""
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": input_filename}},
        "2": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": DEFAULT_UPSCALER}},
        "3": {"class_type": "ImageUpscaleWithModel", "inputs": {
            "upscale_model": ["2", 0], "image": ["1", 0]}},
        "4": {"class_type": "SaveImage", "inputs": {
            "images": ["3", 0], "filename_prefix": output_prefix}},
    }


def submit_prompt(workflow: dict) -> str | None:
    payload = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFYUI_API}/prompt", data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8")).get("prompt_id")
    except Exception as e:
        print(f"    API error: {e}")
        return None


def wait_for_completion(prompt_id: str, timeout: int = 120) -> dict | None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"{COMFYUI_API}/history/{prompt_id}", method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                history = json.loads(resp.read().decode("utf-8"))
                if prompt_id in history:
                    return history[prompt_id]
        except Exception:
            pass
        time.sleep(1.0)
    return None


def get_output_images(history_entry: dict) -> list[Path]:
    paths = []
    for node_output in history_entry.get("outputs", {}).values():
        for img in node_output.get("images", []):
            if img.get("filename"):
                paths.append(COMFYUI_OUTPUT_DIR / img.get("subfolder", "") / img["filename"])
    return paths


def main():
    parser = argparse.ArgumentParser(description="Regenerate damaged tile backgrounds")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from PIL import Image

    # Load biome prompts
    zone_biome = {}
    biome_prompts = {}
    for f in (PROJECT_ROOT / "scenarios").glob("biome_*.yaml"):
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        biome = data.get("biome", {})
        biome_id = biome.get("id", f.stem)
        for zone in data.get("zones", []):
            zid = zone.get("id", "")
            if zid:
                zone_biome[zid.lower()] = biome_id
        prompt = biome.get("assets", {}).get("background", {}).get("prompt", "")
        if prompt:
            biome_prompts[biome_id] = prompt

    # Load tile map
    map_data = json.loads(
        (PROJECT_ROOT / "workspace/shattered_realms/map.json").read_text(encoding="utf-8"))
    tile_map = {tuple(t["position"]): t for t in map_data["tiles"]}

    # Find damaged tiles
    tasks = []
    bg_dir = PROJECT_ROOT / "assets" / "tile_backgrounds" / "shattered_realms"
    for p in sorted(bg_dir.glob("*.png")):
        im = Image.open(p)
        size = im.size
        im.close()
        if size in (ORIGINAL_SIZE, CORRECT_SIZE):
            continue

        parts = p.stem.split("_")
        row, col = int(parts[1]), int(parts[2])
        td = tile_map.get((row, col), {})
        label = (td.get("user_label", "") or td.get("zone_id", "")).lower().replace(" ", "_").replace("'", "")
        terrain = td.get("terrain", "FLOOR")

        # Find prompt: biome match or terrain fallback
        biome_id = zone_biome.get(label, "")
        prompt = biome_prompts.get(biome_id, "")
        if not prompt:
            prompt = TERRAIN_PROMPTS.get(terrain, TERRAIN_PROMPTS["FLOOR"])
            # Add zone label as flavor
            zone_label = td.get("user_label", "") or td.get("zone_id", "")
            if zone_label:
                prompt = f"{zone_label}, {prompt}"

        tasks.append({"path": p, "row": row, "col": col, "prompt": prompt, "terrain": terrain})

    print(f"Found {len(tasks)} damaged images to regenerate")

    if args.dry_run:
        for t in tasks[:10]:
            print(f"  ({t['row']},{t['col']}) {t['path'].name}: \"{t['prompt'][:60]}...\"")
        if len(tasks) > 10:
            print(f"  ... +{len(tasks) - 10} more")
        return

    success = 0
    for i, task in enumerate(tasks):
        print(f"  [{i+1}/{len(tasks)}] tile_{task['row']}_{task['col']} ... ", end="", flush=True)

        # Phase 1: txt2img at 768x512
        prefix = f"regen_{task['row']}_{task['col']}"
        workflow = build_txt2img_workflow(task["prompt"], output_prefix=prefix)
        pid = submit_prompt(workflow)
        if not pid:
            print("FAILED (txt2img submit)")
            continue

        result = wait_for_completion(pid, timeout=120)
        if not result:
            print("TIMEOUT (txt2img)")
            continue

        outputs = get_output_images(result)
        if not outputs or not outputs[0].exists():
            print("NO OUTPUT (txt2img)")
            continue

        gen_path = outputs[0]

        # Save the fresh 768x512 image (will be upscaled by comfyui_batch_upscale.py)
        shutil.copy2(gen_path, task["path"])

        success += 1
        print("OK")

        # Cleanup
        try:
            (COMFYUI_INPUT_DIR / input_name).unlink()
        except Exception:
            pass

        time.sleep(0.5)

    print(f"\nDone: {success}/{len(tasks)} regenerated")


if __name__ == "__main__":
    main()

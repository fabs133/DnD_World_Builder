#!/usr/bin/env python3
"""Batch upscale tile backgrounds and portraits using ComfyUI's ESRGAN upscaler.

Uses the Real-ESRGAN / UltraSharp upscaler node (no SD inference needed),
so each image takes ~2-3 seconds. Upscales in-place or to a target directory.

Usage:
    # Upscale all tile backgrounds (default: 2x final size)
    python tools/comfyui_batch_upscale.py backgrounds

    # Upscale portraits
    python tools/comfyui_batch_upscale.py portraits

    # Upscale everything
    python tools/comfyui_batch_upscale.py all

    # Dry run — list what would be upscaled
    python tools/comfyui_batch_upscale.py backgrounds --dry-run

    # Custom scale factor
    python tools/comfyui_batch_upscale.py backgrounds --scale 3

    # Custom output directory (default: overwrites originals)
    python tools/comfyui_batch_upscale.py backgrounds --output assets/tile_backgrounds_hd

Requires ComfyUI running with an upscaler model (4x-UltraSharp.pth or RealESRGAN_x4plus.pth).
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

# ─── Configuration ──────────────────────────────────────────────────

COMFYUI_API = os.environ.get("COMFYUI_API", "http://127.0.0.1:8000")
COMFYUI_INPUT_DIR = Path(os.environ.get(
    "COMFYUI_INPUT_DIR",
    r"D:\fbrmp\Documents\input",
))
COMFYUI_OUTPUT_DIR = Path(os.environ.get(
    "COMFYUI_OUTPUT_DIR",
    r"D:\fbrmp\Documents\output",
))
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ASSETS = PROJECT_ROOT / "assets"

UPSCALER_MODEL = "4x-UltraSharp.pth"

# Asset directories
BACKGROUNDS_DIR = PROJECT_ASSETS / "tile_backgrounds"
PORTRAITS_DIR = PROJECT_ASSETS / "portraits"


# ─── ComfyUI Workflow ──────────────────────────────────────────────

def build_upscale_workflow(
    input_filename: str,
    upscaler: str = UPSCALER_MODEL,
    output_prefix: str = "upscaled",
) -> dict:
    """Build a ComfyUI workflow that loads an image and upscales it.

    Nodes:
      1: LoadImage — loads from ComfyUI input/ directory
      2: UpscaleModelLoader — loads the ESRGAN model
      3: ImageUpscaleWithModel — applies the upscaler
      4: SaveImage — writes to ComfyUI output/ directory
    """
    return {
        "1": {
            "class_type": "LoadImage",
            "inputs": {
                "image": input_filename,
            },
        },
        "2": {
            "class_type": "UpscaleModelLoader",
            "inputs": {
                "model_name": upscaler,
            },
        },
        "3": {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {
                "upscale_model": ["2", 0],
                "image": ["1", 0],
            },
        },
        "4": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["3", 0],
                "filename_prefix": output_prefix,
            },
        },
    }


# ─── ComfyUI API ─────────────────────────────────────────────────

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


def wait_for_completion(prompt_id: str, timeout: int = 60) -> dict | None:
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
        time.sleep(0.5)
    return None


def get_output_images(history_entry: dict) -> list[Path]:
    """Extract output image paths from a completed prompt."""
    paths = []
    outputs = history_entry.get("outputs", {})
    for node_id, node_output in outputs.items():
        for img in node_output.get("images", []):
            filename = img.get("filename", "")
            subfolder = img.get("subfolder", "")
            if filename:
                paths.append(COMFYUI_OUTPUT_DIR / subfolder / filename)
    return paths


# ─── Image collection ────────────────────────────────────────────

ORIGINAL_SIZE = (768, 512)
TARGET_SIZE = (1536, 1024)  # Correct 2x upscale from 768x512


def collect_backgrounds(skip_upscaled: bool = True) -> list[Path]:
    """Find tile backgrounds that need upscaling (768x512 originals only).

    Skips correctly upscaled images AND damaged double-upscaled ones.
    Use ``list_damaged()`` to find the damaged images separately.
    """
    images = []
    for ext in ("*.png", "*.jpg", "*.jpeg"):
        images.extend(BACKGROUNDS_DIR.rglob(ext))
    if skip_upscaled:
        from PIL import Image
        filtered = []
        for p in images:
            im = Image.open(p)
            size = im.size
            im.close()
            # Only process original-size images
            if size == ORIGINAL_SIZE:
                filtered.append(p)
        return sorted(filtered)
    return sorted(images)


def list_damaged() -> list[Path]:
    """Find images that are neither original size nor correctly upscaled."""
    from PIL import Image
    damaged = []
    for ext in ("*.png", "*.jpg", "*.jpeg"):
        for p in BACKGROUNDS_DIR.rglob(ext):
            im = Image.open(p)
            size = im.size
            im.close()
            if size != ORIGINAL_SIZE and size != TARGET_SIZE:
                damaged.append(p)
    return sorted(damaged)


def collect_portraits() -> list[Path]:
    """Find all portrait images."""
    images = []
    for ext in ("*.png", "*.jpg", "*.jpeg"):
        images.extend(PORTRAITS_DIR.rglob(ext))
    return sorted(images)


# ─── Upscale pipeline ────────────────────────────────────────────

def upscale_batch(
    images: list[Path],
    output_dir: Path | None = None,
    dry_run: bool = False,
    scale: int = 2,
    pause: float = 0.5,
) -> int:
    """Upscale a batch of images through ComfyUI.

    Args:
        images: List of image paths to upscale.
        output_dir: Where to save results. None = overwrite originals.
        dry_run: Just list what would be done.
        scale: Target scale factor (the 4x upscaler output is resized down).
        pause: Seconds between submissions.

    Returns:
        Number of successfully upscaled images.
    """
    total = len(images)
    if total == 0:
        print("No images found to upscale.")
        return 0

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Upscaling {total} images "
          f"(4x ESRGAN -> {scale}x target)")
    print(f"  Upscaler model: {UPSCALER_MODEL}")
    print(f"  Output: {'overwrite originals' if not output_dir else output_dir}")
    print()

    if dry_run:
        for img in images[:20]:
            print(f"  Would upscale: {img.relative_to(PROJECT_ROOT)}")
        if total > 20:
            print(f"  ... and {total - 20} more")
        return 0

    success = 0
    for i, img_path in enumerate(images):
        rel = img_path.relative_to(PROJECT_ROOT)
        print(f"  [{i+1}/{total}] {rel} ... ", end="", flush=True)

        # Copy image to ComfyUI input directory
        input_name = f"upscale_src_{img_path.stem}{img_path.suffix}"
        input_dest = COMFYUI_INPUT_DIR / input_name
        shutil.copy2(img_path, input_dest)

        # Build and submit workflow
        prefix = f"upscaled_{img_path.stem}"
        workflow = build_upscale_workflow(input_name, output_prefix=prefix)
        prompt_id = submit_prompt(workflow)

        if not prompt_id:
            print("FAILED (submit)")
            continue

        # Wait for completion
        result = wait_for_completion(prompt_id, timeout=60)
        if not result:
            print("TIMEOUT")
            continue

        # Find output image
        output_images = get_output_images(result)
        if not output_images:
            print("NO OUTPUT")
            continue

        src = output_images[0]
        if not src.exists():
            print(f"MISSING ({src.name})")
            continue

        # Resize if needed (4x upscaler produces 4x, we may want 2x or 3x)
        if scale < 4:
            try:
                from PIL import Image
                im = Image.open(src)
                orig_w, orig_h = im.size
                # The 4x upscaler produces 4x the original
                # Scale down to target: e.g. for 2x target from 4x output, resize to 50%
                factor = scale / 4.0
                new_w = int(orig_w * factor)
                new_h = int(orig_h * factor)
                im = im.resize((new_w, new_h), Image.LANCZOS)
                im.save(src)
            except ImportError:
                pass  # Skip resize if PIL not available

        # Copy to target location
        if output_dir:
            # Preserve subdirectory structure
            rel_to_assets = img_path.relative_to(PROJECT_ASSETS)
            dest = output_dir / rel_to_assets
            dest.parent.mkdir(parents=True, exist_ok=True)
        else:
            dest = img_path  # Overwrite original

        shutil.copy2(src, dest)
        success += 1
        print(f"OK ({dest.name})")

        # Clean up ComfyUI input file
        try:
            input_dest.unlink()
        except Exception:
            pass

        if pause > 0 and i < total - 1:
            time.sleep(pause)

    print(f"\nDone: {success}/{total} upscaled successfully.")
    return success


# ─── CLI ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Batch upscale game assets via ComfyUI ESRGAN")
    parser.add_argument(
        "target",
        choices=["backgrounds", "portraits", "all"],
        help="Which assets to upscale",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="List what would be upscaled without doing it")
    parser.add_argument("--scale", type=int, default=2,
                        help="Target scale factor (default: 2)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output directory (default: overwrite originals)")
    parser.add_argument("--pause", type=float, default=0.5,
                        help="Seconds between submissions (default: 0.5)")
    parser.add_argument("--list-damaged", action="store_true",
                        help="List double-upscaled/damaged images and exit")

    args = parser.parse_args()

    if args.list_damaged:
        damaged = list_damaged()
        if damaged:
            print(f"{len(damaged)} damaged images (need regeneration, not upscaling):")
            for p in damaged:
                from PIL import Image
                im = Image.open(p)
                print(f"  {im.size[0]}x{im.size[1]}  {p.relative_to(PROJECT_ROOT)}")
                im.close()
        else:
            print("No damaged images found.")
        return
    output_dir = Path(args.output) if args.output else None

    images = []
    if args.target in ("backgrounds", "all"):
        images.extend(collect_backgrounds())
    if args.target in ("portraits", "all"):
        images.extend(collect_portraits())

    upscale_batch(
        images,
        output_dir=output_dir,
        dry_run=args.dry_run,
        scale=args.scale,
        pause=args.pause,
    )


if __name__ == "__main__":
    main()

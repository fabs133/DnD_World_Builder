#!/usr/bin/env python3
"""Batch voice line generator for DnD World Builder.

Reads biome/world YAML files, extracts all entities with voice_lines.needed,
and generates WAV audio files via Chatterbox TTS.

Usage:
    python tools/voice_batch_generator.py scenarios/world_shattered_realms.yaml
    python tools/voice_batch_generator.py scenarios/biome_millhaven.yaml --dry-run
    python tools/voice_batch_generator.py scenarios/world_shattered_realms.yaml --only "Brenna"
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. pip install pyyaml")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ─── Data structures ────────────────────────────────────────────────

@dataclass
class VoiceTask:
    """A single voice line generation task."""
    entity_name: str
    category: str
    index: int
    text: str
    voice_id: str
    preset_name: str
    reference_audio: str | None
    exaggeration: float
    speed_factor: float
    cfg_weight: float
    output_path: str
    cache_key: str


# ─── YAML parsing ───────────────────────────────────────────────────

def _entity_slug(name: str) -> str:
    return name.lower().replace(" ", "_").replace("'", "")


def _parse_entity_tasks(entity_cfg: dict) -> list[VoiceTask]:
    """Extract voice generation tasks from one entity config."""
    voice_lines = entity_cfg.get("voice_lines", {})
    if not voice_lines or not voice_lines.get("needed"):
        return []

    voice = entity_cfg.get("voice")
    if not voice or not isinstance(voice, dict):
        return []

    dialogue = entity_cfg.get("dialogue")
    if not dialogue or not isinstance(dialogue, dict):
        return []

    name = entity_cfg["name"]
    preset = voice.get("preset", "")
    ref_audio = voice.get("reference_audio")
    exaggeration = voice.get("exaggeration", 0.5)
    speed = voice.get("speed", 1.0)
    cfg_weight = voice.get("cfg_weight", 0.5)
    output_dir = voice_lines.get("output_dir", f"assets/voice/{_entity_slug(name)}/")

    # Deterministic voice_id for stable cache keys
    from core.voice.voice_profile import VoiceProfile
    from core.voice.voice_cache import VoiceCache
    voice_id = VoiceProfile.deterministic_voice_id(name, preset)

    tasks = []
    for category, lines in dialogue.items():
        if not isinstance(lines, list):
            continue
        for i, text in enumerate(lines):
            if not text or not isinstance(text, str):
                continue
            cache_key = VoiceCache.compute_cache_key(
                voice_id, text, exaggeration, speed, cfg_weight,
            )
            output_file = f"{output_dir}{category}_{i}.wav"
            tasks.append(VoiceTask(
                entity_name=name,
                category=category,
                index=i,
                text=text,
                voice_id=voice_id,
                preset_name=preset,
                reference_audio=ref_audio,
                exaggeration=exaggeration,
                speed_factor=speed,
                cfg_weight=cfg_weight,
                output_path=output_file,
                cache_key=cache_key,
            ))

    return tasks


def parse_biome_yaml(filepath: Path) -> list[VoiceTask]:
    """Parse a biome YAML and extract voice tasks."""
    data = yaml.safe_load(filepath.read_text(encoding="utf-8"))
    tasks = []
    for entity in data.get("entities", []):
        tasks.extend(_parse_entity_tasks(entity))
    return tasks


def parse_world_yaml(filepath: Path) -> list[VoiceTask]:
    """Parse a world YAML and extract voice tasks from all biomes."""
    data = yaml.safe_load(filepath.read_text(encoding="utf-8"))
    tasks = []
    base_dir = filepath.parent

    # Player characters
    for char in data.get("players", {}).get("characters", []):
        tasks.extend(_parse_entity_tasks(char))

    # All biomes
    biome_files = data.get("world", {}).get("biome_files", {})
    for biome_id, filename in biome_files.items():
        biome_path = base_dir / filename
        if biome_path.exists():
            print(f"  Loading biome: {biome_id} from {filename}")
            tasks.extend(parse_biome_yaml(biome_path))
        else:
            print(f"  [SKIP] {filename} not found")

    return tasks


# ─── Execution ──────────────────────────────────────────────────────

def run_batch(
    tasks: list[VoiceTask],
    dry_run: bool = False,
    pause_between: float = 0.5,
) -> dict:
    """Execute voice generation tasks."""
    summary = {"total": len(tasks), "completed": 0, "failed": 0, "skipped": 0}

    print(f"\n{'='*60}")
    print(f"  VOICE GENERATION — {len(tasks)} lines")
    print(f"{'='*60}\n")

    if dry_run:
        print("[DRY RUN] Would generate:\n")
        current_entity = ""
        for t in tasks:
            if t.entity_name != current_entity:
                current_entity = t.entity_name
                print(f"\n  {t.entity_name} (preset: {t.preset_name}):")
            preview = t.text[:50] + "..." if len(t.text) > 50 else t.text
            print(f"    [{t.category}_{t.index}] \"{preview}\"")
            print(f"      ->{t.output_path}")
        print(f"\n  Total: {len(tasks)} voice lines")
        return summary

    # Check Chatterbox availability
    try:
        from core.voice.voice_engine import VoiceEngine, HardwareTier
    except ImportError:
        print("ERROR: core.voice.voice_engine not available")
        sys.exit(1)

    engine = VoiceEngine.instance()
    tier = engine.detect_hardware()
    if tier == HardwareTier.NONE:
        print("ERROR: Chatterbox TTS not available.")
        print("Install with: pip install chatterbox-tts torch torchaudio")
        sys.exit(1)

    print(f"  Hardware: {tier.value}")
    print(f"  Loading model...")
    if not engine.load_model():
        print("ERROR: Failed to load Chatterbox model")
        sys.exit(1)
    print(f"  Model ready ({engine._model_variant}).\n")

    # Warn about paralinguistic tags if Turbo not available
    if engine._model_variant != "turbo":
        has_tags = any("[" in t.text for t in tasks)
        if has_tags:
            print("  [WARN] Standard Chatterbox model loaded — paralinguistic tags "
                  "like [chuckle] will be spoken as words. Install latest "
                  "chatterbox-tts for Turbo support.\n")

    from core.voice.voice_profile import VoiceProfile

    for i, task in enumerate(tasks, 1):
        # Skip if output already exists
        out_path = PROJECT_ROOT / task.output_path
        if out_path.exists():
            print(f"  [{i}/{len(tasks)}] SKIP (exists): {task.output_path}")
            summary["skipped"] += 1
            continue

        preview = task.text[:40] + "..." if len(task.text) > 40 else task.text
        print(f"  [{i}/{len(tasks)}] {task.entity_name} | {task.category}_{task.index}")
        print(f"    \"{preview}\"")

        profile = VoiceProfile(
            voice_id=task.voice_id,
            source_type="preset",
            preset_name=task.preset_name,
            reference_audio=task.reference_audio,
            exaggeration=task.exaggeration,
            speed_factor=task.speed_factor,
            cfg_weight=task.cfg_weight,
            apply_effects=False,  # Effects crash with CUDA; apply separately
        )

        ref_path = None
        if task.reference_audio:
            ref_path = PROJECT_ROOT / task.reference_audio
            if not ref_path.exists():
                ref_path = None

        start = time.time()
        audio_bytes = engine.generate(task.text, profile, ref_path)
        elapsed = time.time() - start

        if audio_bytes:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(audio_bytes)
            print(f"    Generated: {task.output_path} ({elapsed:.1f}s, {len(audio_bytes)//1024}KB)")
            summary["completed"] += 1
        else:
            print(f"    FAILED ({elapsed:.1f}s)")
            summary["failed"] += 1

        if i < len(tasks):
            time.sleep(pause_between)

    # Write manifests per entity
    _write_manifests(tasks, summary)

    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE")
    print(f"  Completed: {summary['completed']}")
    print(f"  Skipped:   {summary['skipped']}")
    print(f"  Failed:    {summary['failed']}")
    print(f"{'='*60}\n")

    return summary


def _write_manifests(tasks: list[VoiceTask], summary: dict) -> None:
    """Write a manifest.json for each entity's output directory."""
    from collections import defaultdict
    by_entity: dict[str, list[VoiceTask]] = defaultdict(list)
    for t in tasks:
        by_entity[t.entity_name].append(t)

    for entity_name, entity_tasks in by_entity.items():
        output_dir = None
        lines = {}
        for t in entity_tasks:
            out = PROJECT_ROOT / t.output_path
            if output_dir is None:
                output_dir = out.parent
            key = f"{t.category}_{t.index}"
            lines[key] = {
                "text": t.text,
                "file": out.name,
                "cache_key": t.cache_key,
                "exists": out.exists(),
            }

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            manifest = {
                "entity_name": entity_name,
                "lines": lines,
            }
            manifest_path = output_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )


def print_status(tasks: list[VoiceTask]) -> None:
    """Print status report."""
    print(f"\n{'='*60}")
    print(f"  VOICE LINE STATUS — {len(tasks)} total lines")
    print(f"{'='*60}\n")

    from collections import defaultdict
    by_entity: dict[str, list[VoiceTask]] = defaultdict(list)
    for t in tasks:
        by_entity[t.entity_name].append(t)

    total_exists = 0
    total_pending = 0
    for entity_name in sorted(by_entity):
        entity_tasks = by_entity[entity_name]
        exists = sum(1 for t in entity_tasks if (PROJECT_ROOT / t.output_path).exists())
        pending = len(entity_tasks) - exists
        total_exists += exists
        total_pending += pending
        status = "DONE" if pending == 0 else f"{exists}/{len(entity_tasks)}"
        print(f"  {entity_name:30s} {len(entity_tasks):3d} lines  [{status}]")

    print(f"\n  TOTAL: {len(tasks)} lines | {total_exists} generated | {total_pending} pending\n")


# ─── CLI ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Batch generate voice lines via Chatterbox TTS")
    parser.add_argument("input", type=Path, help="YAML file (biome_*.yaml or world_*.yaml)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated")
    parser.add_argument("--status", action="store_true", help="Print status report")
    parser.add_argument("--only", type=str, default=None, help="Filter to entity name (substring match)")
    parser.add_argument("--pause", type=float, default=0.5, help="Seconds between tasks")

    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: {args.input} not found")
        sys.exit(1)

    print(f"Loading: {args.input}")

    if args.input.name.startswith("world_"):
        tasks = parse_world_yaml(args.input)
    else:
        tasks = parse_biome_yaml(args.input)

    if args.only:
        tasks = [t for t in tasks if args.only.lower() in t.entity_name.lower()]

    if not tasks:
        print("No voice tasks found.")
        sys.exit(0)

    if args.status:
        print_status(tasks)
        sys.exit(0)

    summary = run_batch(tasks, dry_run=args.dry_run, pause_between=args.pause)
    if summary.get("failed", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

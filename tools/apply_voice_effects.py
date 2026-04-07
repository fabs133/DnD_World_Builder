#!/usr/bin/env python3
"""Apply preset-specific audio effects to generated voice WAV files.

Runs Pedalboard effects (reverb, chorus, compression) on voice lines
based on the preset associated with each entity. This is a standalone
post-processing step — separate from TTS generation to avoid
Pedalboard/CUDA native conflicts.

Usage:
    python tools/apply_voice_effects.py scenarios/world_shattered_realms.yaml
    python tools/apply_voice_effects.py scenarios/biome_millhaven.yaml --dry-run
"""

from __future__ import annotations

import argparse
import io
import sys
import wave
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. pip install pyyaml")
    sys.exit(1)


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def collect_voice_tasks(yaml_path: Path) -> list[dict]:
    """Extract entity → preset_name → voice file mappings from YAML."""
    tasks = []
    base_dir = yaml_path.parent

    data = load_yaml(yaml_path)

    # World YAML: load all biomes
    if "world" in data:
        biome_files = data.get("world", {}).get("biome_files", {})
        for biome_id, filename in biome_files.items():
            biome_path = base_dir / filename
            if biome_path.exists():
                tasks.extend(_extract_from_biome(load_yaml(biome_path)))
    else:
        # Single biome YAML
        tasks.extend(_extract_from_biome(data))

    return tasks


def _extract_from_biome(biome_data: dict) -> list[dict]:
    tasks = []
    for entity in biome_data.get("entities", []):
        voice = entity.get("voice", {})
        if not voice:
            continue
        preset_name = voice.get("preset", "")
        voice_lines = entity.get("voice_lines", {})
        output_dir = voice_lines.get("output_dir", "")
        if not output_dir or not preset_name:
            continue

        # Find all WAV files in the output directory
        wav_dir = PROJECT_ROOT / output_dir
        if wav_dir.exists():
            for wav_file in sorted(wav_dir.glob("*.wav")):
                tasks.append({
                    "entity_name": entity.get("name", ""),
                    "preset_name": preset_name,
                    "wav_path": str(wav_file),
                })
    return tasks


def read_wav(path: str) -> tuple[np.ndarray, int]:
    """Read WAV file and return (samples_float32, sample_rate)."""
    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
    return samples, sr


def write_wav(path: str, samples: np.ndarray, sr: int) -> None:
    """Write float32 samples to 16-bit PCM WAV."""
    pcm = (samples * 32767).astype(np.int16).tobytes()
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm)


def main():
    parser = argparse.ArgumentParser(description="Apply voice effects to WAV files")
    parser.add_argument("input", type=Path, help="World or biome YAML file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be processed without modifying files")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: {args.input} not found")
        sys.exit(1)

    # Import effects (no CUDA in this process)
    from core.voice.voice_effects import apply_voice_effects, _build_effects_chains
    chains = _build_effects_chains()
    if not chains:
        print("ERROR: pedalboard not installed. Install with: pip install pedalboard")
        sys.exit(1)

    print(f"Loading: {args.input}")
    tasks = collect_voice_tasks(args.input)
    print(f"  Found {len(tasks)} voice files\n")

    # Filter to only presets that have effects
    tasks_with_effects = [t for t in tasks if t["preset_name"] in chains]
    tasks_no_effects = [t for t in tasks if t["preset_name"] not in chains]

    print(f"  With effects: {len(tasks_with_effects)}")
    print(f"  No effects (clean): {len(tasks_no_effects)}\n")

    if args.dry_run:
        for t in tasks_with_effects:
            print(f"  [WOULD PROCESS] {t['preset_name']:20s} {t['wav_path']}")
        print(f"\nDry run: {len(tasks_with_effects)} files would be processed")
        return

    processed = 0
    failed = 0
    for i, task in enumerate(tasks_with_effects, 1):
        wav_path = task["wav_path"]
        preset = task["preset_name"]
        try:
            samples, sr = read_wav(wav_path)
            effected = apply_voice_effects(samples, sr, preset)
            write_wav(wav_path, effected, sr)
            processed += 1
            print(f"  [{i}/{len(tasks_with_effects)}] {preset:20s} {Path(wav_path).name}")
        except Exception as e:
            failed += 1
            print(f"  [{i}/{len(tasks_with_effects)}] FAILED {Path(wav_path).name}: {e}")

    print(f"\n  Processed: {processed}")
    print(f"  Failed:    {failed}")
    print(f"  Skipped:   {len(tasks_no_effects)} (no effects for preset)")


if __name__ == "__main__":
    main()

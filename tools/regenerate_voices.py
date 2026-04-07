#!/usr/bin/env python3
"""Regenerate voice lines for NPCs using their assigned voice presets.

Reads the scenario map.json, finds all NPCs with voice_preset + dialogue_lines,
and generates WAV files via Chatterbox TTS using the preset's reference audio.

Usage:
    python tools/regenerate_voices.py workspace/shattered_realms/map.json
    python tools/regenerate_voices.py workspace/shattered_realms/map.json --only "Brenna"
    python tools/regenerate_voices.py workspace/shattered_realms/map.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def entity_slug(name: str) -> str:
    return name.lower().replace(" ", "_").replace("'", "")


def _apply_voice_overrides(base_profile, node):
    """Create a copy of the voice profile with emotion + node overrides applied."""
    from copy import deepcopy
    profile = deepcopy(base_profile)
    voice_params = node.get_voice_params()
    for key, value in voice_params.items():
        if hasattr(profile, key):
            setattr(profile, key, value)
    return profile


def main():
    parser = argparse.ArgumentParser(description="Regenerate NPC voice lines")
    parser.add_argument("map_json", help="Path to scenario map.json")
    parser.add_argument("--only", help="Only generate for this NPC name (substring match)")
    parser.add_argument("--dry-run", action="store_true", help="List what would be generated")
    args = parser.parse_args()

    map_path = Path(args.map_json)
    data = json.loads(map_path.read_text(encoding="utf-8"))

    # Collect NPCs with voice presets and dialogue
    npcs = []
    for tile in data.get("tiles", []):
        for e in tile.get("entities", []):
            preset_id = e.get("voice_preset")
            dialogue = e.get("dialogue_lines", {})
            if preset_id and dialogue:
                if args.only and args.only.lower() not in e["name"].lower():
                    continue
                npcs.append(e)

    if not npcs:
        print("No matching NPCs with voice_preset + dialogue found.")
        return

    print(f"Found {len(npcs)} NPCs to generate voices for:\n")

    # Load preset registry
    from core.voice.voice_preset_registry import get_preset

    # Build task list
    tasks = []
    for e in npcs:
        name = e["name"]
        preset_id = e["voice_preset"]
        preset = get_preset(preset_id)
        if not preset:
            print(f"  WARNING: Unknown preset '{preset_id}' for {name}, skipping")
            continue

        profile = preset.to_voice_profile()
        slug = entity_slug(name)
        output_dir = PROJECT_ROOT / "assets" / "voice" / slug

        # Prefer dialogue_graph (with emotion overrides), fall back to flat lines
        graph_data = e.get("dialogue_graph")
        if graph_data:
            from models.dialogue.dialogue_graph import DialogueGraph
            graph = DialogueGraph.from_dict(graph_data)
            for node_id, node in graph.nodes.items():
                if not node.text:
                    continue
                output_file = output_dir / f"{node_id}.wav"
                # Build profile with emotion overrides
                node_profile = _apply_voice_overrides(profile, node)
                tasks.append({
                    "name": name,
                    "preset": preset_id,
                    "category": node.category,
                    "index": 0,
                    "text": node.text,
                    "output": output_file,
                    "profile": node_profile,
                    "node_id": node_id,
                })
        else:
            # Fall back to old dialogue_lines format
            dialogue = e.get("dialogue_lines", {})
            for category, lines in dialogue.items():
                if not isinstance(lines, list):
                    continue
                for i, text in enumerate(lines):
                    if not text:
                        continue
                    output_file = output_dir / f"{category}_{i}.wav"
                    tasks.append({
                        "name": name,
                        "preset": preset_id,
                        "category": category,
                        "index": i,
                        "text": text,
                        "output": output_file,
                        "profile": profile,
                    })

        line_count = sum(1 for t in tasks if t["name"] == name)
        ref = profile.reference_audio or "default"
        print(f"  {name}: {line_count} lines, preset={preset_id}, ref={Path(ref).name}")

    print(f"\nTotal: {len(tasks)} voice lines to generate")

    if args.dry_run:
        print("\n[DRY RUN] Would generate:")
        for t in tasks[:10]:
            print(f"  {t['name']} / {t['category']}_{t['index']}: \"{t['text'][:50]}...\"")
        if len(tasks) > 10:
            print(f"  ... and {len(tasks) - 10} more")
        return

    # Load TTS engine
    print("\nLoading Chatterbox TTS...")
    from core.voice.voice_engine import VoiceEngine
    engine = VoiceEngine.instance()
    if not engine.load_model():
        print("ERROR: Failed to load TTS model")
        return

    print(f"Model loaded. Generating {len(tasks)} voice lines...\n")

    success = 0
    for i, task in enumerate(tasks):
        print(f"  [{i+1}/{len(tasks)}] {task['name']} / {task['category']}_{task['index']} ... ",
              end="", flush=True)

        profile = task["profile"]
        ref_path = None
        if profile.reference_audio:
            ref_path = Path(profile.reference_audio)
            if not ref_path.exists():
                print(f"SKIP (ref not found: {ref_path.name})")
                continue

        audio_bytes = engine.generate(task["text"], profile, reference_audio_path=ref_path)
        if not audio_bytes:
            print("FAILED (no output)")
            continue

        output = task["output"]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(audio_bytes)
        success += 1
        print("OK")

    # Write manifest files for each NPC
    manifests = {}
    for t in tasks:
        slug = entity_slug(t["name"])
        if slug not in manifests:
            manifests[slug] = []
        out = t["output"]
        if out.exists():
            manifests[slug].append({
                "category": t["category"],
                "index": t["index"],
                "text": t["text"],
                "file": out.name,
            })

    for slug, entries in manifests.items():
        # Build manifest in the format expected by npc_conversation_dialog
        lines_dict = {}
        for entry in entries:
            key = f"{entry['category']}_{entry['index']}"
            lines_dict[key] = {
                "text": entry["text"],
                "file": entry["file"],
                "exists": True,
            }
        manifest_path = PROJECT_ROOT / "assets" / "voice" / slug / "manifest.json"
        manifest_path.write_text(
            json.dumps({"lines": lines_dict}, indent=2), encoding="utf-8")

    # Update map.json with voice_lines_dir for each NPC
    updated = 0
    for tile in data.get("tiles", []):
        for e in tile.get("entities", []):
            if e.get("voice_preset") and e.get("dialogue_lines"):
                slug = entity_slug(e["name"])
                e["voice_lines_dir"] = f"assets/voice/{slug}"
                updated += 1

    map_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nDone: {success}/{len(tasks)} generated, {updated} entities updated in map.json")


if __name__ == "__main__":
    main()

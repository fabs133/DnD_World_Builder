"""DM-side coordinator for distributed voice generation.

Assigns whole characters to workers via greedy bin-packing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WorkerInfo:
    player_id: str
    player_name: str
    hardware_tier: str  # "gpu", "cpu", "none"
    vram_mb: int = 0
    assigned_characters: list[str] = field(default_factory=list)
    assigned_line_count: int = 0
    completed_characters: list[str] = field(default_factory=list)


@dataclass
class CharacterWork:
    character_id: str
    entity_name: str
    voice_seed_path: Optional[str]
    params: dict
    lines: list[dict]
    assigned_to: Optional[str] = None  # player_id
    completed: bool = False


class VoiceSwarmOrchestrator:
    """DM-side coordinator for distributed character voice generation.

    Greedy bin-packing: sort characters by line count descending,
    assign each to the worker with the least total assigned lines.
    """

    def __init__(self, voice_cache: Any = None, voice_line_provider: Any = None):
        self._workers: Dict[str, WorkerInfo] = {}
        self._characters: Dict[str, CharacterWork] = {}
        self._cache = voice_cache
        self._provider = voice_line_provider
        self._all_complete_callback: Any = None

    def register_worker(
        self, player_id: str, player_name: str, capability: dict,
    ) -> None:
        self._workers[player_id] = WorkerInfo(
            player_id=player_id,
            player_name=player_name,
            hardware_tier=capability.get("hardware_tier", "none"),
            vram_mb=capability.get("vram_mb", 0),
        )

    def start_generation(self, voiced_entities: list[Any]) -> Dict[str, list[str]]:
        """Build character list and assign to workers.

        Returns: {player_id: [character_id, ...]} assignment map.
        """
        # Build character work items
        self._characters.clear()
        for entity in voiced_entities:
            profile = getattr(entity, "voice_profile", None)
            if not profile or not profile.is_voiced:
                continue

            lines = []
            if self._provider:
                voice_lines = self._provider.get_lines_for_entity(entity)
                lines = [
                    {"cache_key": vl.cache_key, "text": vl.text, "category": vl.category}
                    for vl in voice_lines
                ]

            # Skip fully cached characters
            if self._cache and lines:
                uncached = [l for l in lines if not self._cache.has(l["cache_key"])]
                if not uncached:
                    continue
                lines = uncached

            if not lines:
                continue

            char_id = entity.name.lower().replace(" ", "_")
            self._characters[char_id] = CharacterWork(
                character_id=char_id,
                entity_name=entity.name,
                voice_seed_path=profile.reference_audio,
                params={
                    "exaggeration": profile.exaggeration,
                    "speed_factor": profile.speed_factor,
                    "cfg_weight": profile.cfg_weight,
                    "language": profile.language,
                },
                lines=lines,
            )

        # Sort by line count descending (largest first)
        sorted_chars = sorted(
            self._characters.values(),
            key=lambda c: len(c.lines),
            reverse=True,
        )

        # Greedy bin-pack
        assignments: Dict[str, list[str]] = {pid: [] for pid in self._workers}

        for char in sorted_chars:
            worker = self._pick_worker(char)
            if worker is None:
                continue
            char.assigned_to = worker.player_id
            worker.assigned_characters.append(char.character_id)
            worker.assigned_line_count += len(char.lines)
            assignments[worker.player_id].append(char.character_id)

        return assignments

    def _pick_worker(self, char: CharacterWork) -> Optional[WorkerInfo]:
        """Pick the least-loaded eligible worker."""
        eligible = []
        for w in self._workers.values():
            if w.hardware_tier == "none":
                continue
            if w.hardware_tier == "cpu" and len(char.lines) > 5:
                continue
            eligible.append(w)

        if not eligible:
            return None

        return min(eligible, key=lambda w: w.assigned_line_count)

    def get_character_work(self, character_id: str) -> Optional[CharacterWork]:
        return self._characters.get(character_id)

    def handle_progress(self, player_id: str, data: dict) -> None:
        char_id = data.get("character_id", "")
        completed = data.get("completed", 0)
        total = data.get("total", 0)
        logger.info(f"Worker {player_id}: {char_id} {completed}/{total}")

    def handle_character_complete(self, player_id: str, data: dict) -> dict | None:
        """Handle completion. Returns results for cache sync broadcast."""
        char_id = data.get("character_id", "")
        char = self._characters.get(char_id)
        if char is None:
            return None

        char.completed = True

        worker = self._workers.get(player_id)
        if worker:
            worker.completed_characters.append(char_id)

        # Cache results
        results = data.get("results", [])
        if self._cache:
            import base64
            for r in results:
                audio = base64.b64decode(r.get("audio_base64", ""))
                if audio:
                    self._cache.put(r["cache_key"], audio, data.get("entity_name", ""), r.get("text", ""))

        # Check all complete
        if all(c.completed for c in self._characters.values()):
            logger.info("All characters generated")
            if self._all_complete_callback:
                self._all_complete_callback()

        return {"character_id": char_id, "entity_name": data.get("entity_name", ""), "results": results}

    def handle_worker_disconnect(self, player_id: str) -> list[str]:
        """Reassign unstarted characters from disconnected worker.

        Returns list of character_ids that need reassignment.
        """
        worker = self._workers.pop(player_id, None)
        if not worker:
            return []

        to_reassign = []
        for char_id in worker.assigned_characters:
            char = self._characters.get(char_id)
            if char and not char.completed:
                char.assigned_to = None
                to_reassign.append(char_id)

        # Re-assign to remaining workers
        for char_id in to_reassign:
            char = self._characters.get(char_id)
            if char:
                new_worker = self._pick_worker(char)
                if new_worker:
                    char.assigned_to = new_worker.player_id
                    new_worker.assigned_characters.append(char_id)
                    new_worker.assigned_line_count += len(char.lines)

        return to_reassign

    def get_stats(self) -> dict:
        total_chars = len(self._characters)
        completed = sum(1 for c in self._characters.values() if c.completed)
        return {
            "total_characters": total_chars,
            "completed_characters": completed,
            "workers": len(self._workers),
            "per_worker": {
                w.player_name: {
                    "assigned": len(w.assigned_characters),
                    "completed": len(w.completed_characters),
                    "tier": w.hardware_tier,
                }
                for w in self._workers.values()
            },
        }

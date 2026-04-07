"""Background voice generation queue with spatial prediction."""

from __future__ import annotations

import heapq
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from core.voice.voice_profile import VoiceProfile

logger = logging.getLogger(__name__)


@dataclass(order=True)
class VoiceJob:
    """A prioritized voice generation task."""
    effective_priority: int
    entity_name: str = field(compare=False)
    voice_profile: Any = field(compare=False)
    text: str = field(compare=False)
    line_priority: int = field(compare=False)
    tile_distance: int = field(compare=False)
    cache_key: str = field(compare=False)
    tile_pos: tuple = field(compare=False, default=(0, 0))
    created_at: float = field(compare=False, default_factory=time.time)


class VoiceGenerationQueue:
    """Spatial prediction queue with background generation worker.

    BFS flood-fill from player position determines tile distances.
    Lines are prioritized by line_priority + tile_distance.
    """

    def __init__(
        self,
        voice_engine: Any,
        voice_cache: Any,
        voice_line_provider: Any,
        world_tile_manager: Any,
        max_distance: int = 3,
    ):
        self._engine = voice_engine
        self._cache = voice_cache
        self._provider = voice_line_provider
        self._tile_manager = world_tile_manager
        self._max_distance = max_distance

        self._heap: list[VoiceJob] = []
        self._lock = threading.Lock()
        self._running = False
        self._worker_thread: threading.Thread | None = None
        self._swarm_mode = False
        self._player_pos: Tuple[int, int] = (0, 0)
        self._stats = {"generated": 0, "cache_hits": 0}

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        if not self._swarm_mode:
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()
        logger.info("Voice generation queue started (swarm=%s)", self._swarm_mode)

    def stop(self) -> None:
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
            self._worker_thread = None
        logger.info("Voice generation queue stopped")

    def set_swarm_mode(self, enabled: bool) -> None:
        """Enable/disable swarm mode.

        When enabled, the local worker thread is not started — generation
        is handled by the swarm orchestrator + remote workers instead.
        When disabled (or on disconnect), the local worker resumes.
        """
        was_swarm = self._swarm_mode
        self._swarm_mode = enabled
        if was_swarm and not enabled and self._running and self._worker_thread is None:
            # Swarm disabled while running — start local worker
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()
            logger.info("Swarm mode disabled, local worker resumed")

    @property
    def swarm_mode(self) -> bool:
        return self._swarm_mode

    def set_player_position(self, tile_pos: Tuple[int, int]) -> None:
        self._player_pos = tile_pos
        self._rebuild_queue()

    def request_immediate(
        self, text: str, profile: VoiceProfile, entity_name: str,
    ) -> Optional[Any]:
        from core.voice.voice_cache import VoiceCache
        cache_key = VoiceCache.compute_cache_key(
            profile.voice_id, text, profile.exaggeration,
            profile.speed_factor, profile.cfg_weight,
        )
        path = self._cache.get(cache_key)
        if path:
            self._stats["cache_hits"] += 1
            return path

        job = VoiceJob(
            effective_priority=0,
            entity_name=entity_name,
            voice_profile=profile,
            text=text,
            line_priority=0,
            tile_distance=0,
            cache_key=cache_key,
        )
        with self._lock:
            heapq.heappush(self._heap, job)
        return None

    def get_queue_stats(self) -> dict:
        with self._lock:
            queued = len(self._heap)
        return {
            "queued": queued,
            "generated": self._stats["generated"],
            "cache_hits": self._stats["cache_hits"],
        }

    # ── BFS ──────────────────────────────────────────────────────────

    def bfs_distances(self, origin: Tuple[int, int]) -> Dict[Tuple[int, int], int]:
        """BFS flood-fill from origin. Returns {tile_pos: distance}."""
        distances: Dict[Tuple[int, int], int] = {origin: 0}
        queue: deque[Tuple[int, int]] = deque([origin])

        while queue:
            pos = queue.popleft()
            dist = distances[pos]
            if dist >= self._max_distance:
                continue

            adjacent = []
            if self._tile_manager and hasattr(self._tile_manager, "get_adjacent_tiles"):
                adjacent = self._tile_manager.get_adjacent_tiles(pos[0], pos[1])

            for adj in adjacent:
                if adj not in distances:
                    distances[adj] = dist + 1
                    queue.append(adj)

        return distances

    # ── Queue rebuild ────────────────────────────────────────────────

    def _rebuild_queue(self) -> None:
        distances = self.bfs_distances(self._player_pos)
        new_heap: list[VoiceJob] = []

        for tile_pos, dist in distances.items():
            tile = None
            if self._tile_manager and hasattr(self._tile_manager, "tiles"):
                tile = self._tile_manager.tiles.get(tile_pos)
            if tile is None:
                continue

            lines = self._provider.get_lines_for_tile(tile)
            for line in lines:
                if self._cache.has(line.cache_key):
                    continue
                job = VoiceJob(
                    effective_priority=line.line_priority + dist,
                    entity_name=line.entity_name,
                    voice_profile=line.voice_profile,
                    text=line.text,
                    line_priority=line.line_priority,
                    tile_distance=dist,
                    cache_key=line.cache_key,
                    tile_pos=tile_pos,
                )
                heapq.heappush(new_heap, job)

        with self._lock:
            self._heap = new_heap

    # ── Worker ───────────────────────────────────────────────────────

    def _worker_loop(self) -> None:
        while self._running:
            job = self._pop_next_job()
            if job is None:
                time.sleep(0.5)
                continue

            if self._cache.has(job.cache_key):
                continue

            audio_bytes = self._engine.generate(job.text, job.voice_profile)
            if audio_bytes:
                self._cache.put(job.cache_key, audio_bytes, job.entity_name, job.text)
                self._stats["generated"] += 1

                try:
                    from core.gameCreation.event_bus import EventBus
                    from core.events import VOICE_LINE_READY
                    EventBus.emit(VOICE_LINE_READY, {
                        "cache_key": job.cache_key,
                        "entity_name": job.entity_name,
                        "text": job.text,
                    })
                except Exception:
                    pass

    def _pop_next_job(self) -> Optional[VoiceJob]:
        with self._lock:
            if self._heap:
                return heapq.heappop(self._heap)
        return None

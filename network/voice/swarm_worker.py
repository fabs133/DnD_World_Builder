"""Client-side voice generation worker for swarm mode.

Processes one character at a time. All lines for a character are
generated with the same seed for voice consistency.
"""

from __future__ import annotations

import base64
import logging
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class SwarmWorker:
    """Client-side voice generation worker.

    Receives character assignments, generates all lines locally,
    sends batch results back.
    """

    def __init__(
        self,
        voice_engine: Any,
        voice_cache: Any,
        on_progress: Callable[[dict], None] | None = None,
        on_complete: Callable[[dict], None] | None = None,
    ):
        self._engine = voice_engine
        self._cache = voice_cache
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._running = False
        self._thread: threading.Thread | None = None
        self._queue: list[dict] = []
        self._lock = threading.Lock()

    def get_capability(self) -> dict:
        """Report this client's hardware capability."""
        tier = "none"
        vram = 0
        if self._engine:
            hw = self._engine.detect_hardware()
            tier = hw.value
        return {
            "hardware_tier": tier,
            "vram_mb": vram,
            "chatterbox_version": "",
        }

    def handle_character_assign(self, data: dict) -> None:
        """Queue a character assignment for processing."""
        with self._lock:
            self._queue.append(data)
        if not self._running:
            self._start()

    def handle_cache_sync(self, data: dict) -> None:
        """Save received audio to local cache."""
        if not self._cache:
            return
        for result in data.get("results", []):
            audio_b64 = result.get("audio_base64", "")
            if audio_b64:
                audio = base64.b64decode(audio_b64)
                self._cache.put(
                    result["cache_key"], audio,
                    data.get("entity_name", ""), result.get("text", ""),
                )

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    def _start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def _worker_loop(self) -> None:
        while self._running:
            data = self._pop_next()
            if data is None:
                time.sleep(0.5)
                continue
            self._process_character(data)

    def _pop_next(self) -> dict | None:
        with self._lock:
            if self._queue:
                return self._queue.pop(0)
        return None

    def _process_character(self, data: dict) -> None:
        """Generate all lines for one character."""
        character_id = data.get("character_id", "")
        entity_name = data.get("entity_name", "")
        seed_b64 = data.get("voice_seed_base64", "")
        params = data.get("params", {})
        lines = data.get("lines", [])

        # Decode seed to temp file
        seed_path = None
        if seed_b64:
            seed_bytes = base64.b64decode(seed_b64)
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.write(seed_bytes)
            tmp.close()
            seed_path = Path(tmp.name)

        from core.voice.voice_profile import VoiceProfile
        profile = VoiceProfile(
            source_type="preset",
            reference_audio=str(seed_path) if seed_path else None,
            exaggeration=params.get("exaggeration", 0.5),
            speed_factor=params.get("speed_factor", 1.0),
            cfg_weight=params.get("cfg_weight", 0.5),
            language=params.get("language", "en"),
        )

        results = []
        start_time = time.time()

        for i, line in enumerate(lines):
            cache_key = line.get("cache_key", "")
            text = line.get("text", "")

            # Skip if already cached
            if self._cache and self._cache.has(cache_key):
                continue

            audio_bytes = self._engine.generate(text, profile, seed_path)
            if audio_bytes:
                # Save locally
                if self._cache:
                    self._cache.put(cache_key, audio_bytes, entity_name, text)

                audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
                results.append({
                    "cache_key": cache_key,
                    "text": text,
                    "audio_base64": audio_b64,
                    "size_bytes": len(audio_bytes),
                })

            # Report progress every 3 lines
            if (i + 1) % 3 == 0 and self._on_progress:
                self._on_progress({
                    "character_id": character_id,
                    "completed": i + 1,
                    "total": len(lines),
                })

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Send complete batch
        if self._on_complete:
            self._on_complete({
                "character_id": character_id,
                "entity_name": entity_name,
                "results": results,
                "total_generation_time_ms": elapsed_ms,
            })

        # Cleanup temp seed file
        if seed_path and seed_path.exists():
            try:
                seed_path.unlink()
            except OSError:
                pass

        logger.info(
            f"SwarmWorker: {character_id} done — {len(results)} lines in {elapsed_ms}ms"
        )

"""File-based voice audio cache with LRU eviction."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class VoiceCache:
    """File-based LRU cache for generated voice audio.

    Cache key: SHA-256 of (voice_id + text + params).
    """

    def __init__(self, cache_dir: Path, max_size_mb: int = 500):
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._max_size_mb = max_size_mb
        self._manifest: Dict[str, dict] = {}
        self._manifest_path = self._cache_dir / "manifest.json"
        self._write_count = 0
        self.load_manifest()

    @staticmethod
    def compute_cache_key(
        voice_id: str, text: str,
        exaggeration: float = 0.5, speed_factor: float = 1.0, cfg_weight: float = 0.5,
    ) -> str:
        raw = f"{voice_id}|{text}|{exaggeration:.2f}|{speed_factor:.2f}|{cfg_weight:.2f}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def has(self, cache_key: str) -> bool:
        if cache_key not in self._manifest:
            return False
        entry = self._manifest[cache_key]
        path = self._cache_dir / entry["file"]
        return path.exists()

    def get(self, cache_key: str) -> Optional[Path]:
        if not self.has(cache_key):
            return None
        entry = self._manifest[cache_key]
        entry["last_used"] = time.time()
        return self._cache_dir / entry["file"]

    def put(self, cache_key: str, audio_data: bytes, entity_name: str, text: str) -> Path:
        slug = entity_name.lower().replace(" ", "_")
        entity_dir = self._cache_dir / slug
        entity_dir.mkdir(exist_ok=True)

        file_path = entity_dir / f"{cache_key}.wav"
        file_path.write_bytes(audio_data)

        self._manifest[cache_key] = {
            "file": f"{slug}/{cache_key}.wav",
            "entity": entity_name,
            "text": text[:100],
            "created": time.time(),
            "last_used": time.time(),
            "size": len(audio_data),
        }

        self._write_count += 1
        if self._write_count % 10 == 0:
            self.save_manifest()

        if self.get_size_mb() > self._max_size_mb:
            self.evict_lru(self._max_size_mb)

        return file_path

    def evict_lru(self, target_size_mb: int, protected_tiles: Set[Tuple[int, int]] | None = None) -> int:
        if not self._manifest:
            return 0

        entries = sorted(self._manifest.items(), key=lambda kv: kv[1]["last_used"])
        evicted = 0

        for key, entry in entries:
            if self.get_size_mb() <= target_size_mb:
                break
            file_path = self._cache_dir / entry["file"]
            if file_path.exists():
                file_path.unlink()
            del self._manifest[key]
            evicted += 1

        self.save_manifest()
        return evicted

    def get_size_mb(self) -> float:
        total = sum(e.get("size", 0) for e in self._manifest.values())
        return total / (1024 * 1024)

    def get_stats(self) -> dict:
        entities: dict[str, int] = {}
        for entry in self._manifest.values():
            name = entry.get("entity", "unknown")
            entities[name] = entities.get(name, 0) + 1
        return {
            "total_entries": len(self._manifest),
            "total_size_mb": round(self.get_size_mb(), 2),
            "entries_per_entity": entities,
        }

    def clear_entity(self, entity_name: str) -> int:
        to_remove = [k for k, v in self._manifest.items() if v.get("entity") == entity_name]
        for key in to_remove:
            entry = self._manifest[key]
            path = self._cache_dir / entry["file"]
            if path.exists():
                path.unlink()
            del self._manifest[key]
        self.save_manifest()
        return len(to_remove)

    def save_manifest(self) -> None:
        self._manifest_path.write_text(json.dumps(self._manifest, indent=2))

    def load_manifest(self) -> None:
        if self._manifest_path.exists():
            try:
                self._manifest = json.loads(self._manifest_path.read_text())
            except (json.JSONDecodeError, OSError):
                self._manifest = {}

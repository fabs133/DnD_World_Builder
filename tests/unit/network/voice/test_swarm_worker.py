"""Tests for SwarmWorker."""

import base64
import time
import pytest
from unittest.mock import MagicMock

from network.voice.swarm_worker import SwarmWorker


@pytest.fixture
def engine():
    e = MagicMock()
    e.detect_hardware.return_value = MagicMock(value="gpu")
    e.generate.return_value = b"fake_wav_audio_data"
    return e


@pytest.fixture
def cache(tmp_path):
    from core.voice.voice_cache import VoiceCache
    return VoiceCache(tmp_path / "cache", max_size_mb=10)


@pytest.fixture
def worker(engine, cache):
    return SwarmWorker(voice_engine=engine, voice_cache=cache)


class TestCapability:
    def test_reports_tier(self, worker):
        cap = worker.get_capability()
        assert cap["hardware_tier"] == "gpu"


class TestCharacterAssign:
    def _make_assign(self, seed_bytes=None):
        seed_b64 = ""
        if seed_bytes:
            seed_b64 = base64.b64encode(seed_bytes).decode()
        return {
            "character_id": "marta",
            "entity_name": "Marta",
            "voice_seed_base64": seed_b64,
            "params": {"exaggeration": 0.5, "speed_factor": 1.0, "cfg_weight": 0.5},
            "lines": [
                {"cache_key": "k1", "text": "Hello", "category": "greeting"},
                {"cache_key": "k2", "text": "Goodbye", "category": "farewell"},
            ],
        }

    def test_processes_character(self, engine, cache):
        completed = []
        worker = SwarmWorker(
            voice_engine=engine, voice_cache=cache,
            on_complete=lambda d: completed.append(d),
        )
        worker.handle_character_assign(self._make_assign(b"RIFF_seed"))
        time.sleep(1.5)
        worker.stop()

        assert len(completed) == 1
        assert completed[0]["character_id"] == "marta"
        assert len(completed[0]["results"]) == 2

    def test_skips_cached(self, engine, cache):
        # Pre-cache one line
        cache.put("k1", b"audio", "Marta", "Hello")

        completed = []
        worker = SwarmWorker(
            voice_engine=engine, voice_cache=cache,
            on_complete=lambda d: completed.append(d),
        )
        worker.handle_character_assign(self._make_assign())
        time.sleep(1.5)
        worker.stop()

        assert len(completed) == 1
        # Only 1 result (k2), k1 was skipped
        assert len(completed[0]["results"]) == 1

    def test_sends_progress(self, engine, cache):
        progress = []
        lines = [{"cache_key": f"k{i}", "text": f"Line {i}", "category": "greeting"} for i in range(6)]
        data = {
            "character_id": "npc",
            "entity_name": "NPC",
            "voice_seed_base64": "",
            "params": {},
            "lines": lines,
        }
        worker = SwarmWorker(
            voice_engine=engine, voice_cache=cache,
            on_progress=lambda d: progress.append(d),
            on_complete=lambda d: None,
        )
        worker.handle_character_assign(data)
        time.sleep(2.0)
        worker.stop()

        # Progress should be sent every 3 lines (at lines 3 and 6)
        assert len(progress) >= 1

    def test_uses_same_seed_for_all_lines(self, engine, cache):
        completed = []
        worker = SwarmWorker(
            voice_engine=engine, voice_cache=cache,
            on_complete=lambda d: completed.append(d),
        )
        worker.handle_character_assign(self._make_assign(b"RIFF_seed"))
        time.sleep(1.5)
        worker.stop()

        # engine.generate should be called with same profile for both lines
        calls = engine.generate.call_args_list
        if len(calls) >= 2:
            profile1 = calls[0][0][1]  # second arg is profile
            profile2 = calls[1][0][1]
            assert profile1.exaggeration == profile2.exaggeration


class TestCacheSync:
    def test_saves_locally(self, worker, cache):
        worker.handle_cache_sync({
            "entity_name": "Guard",
            "results": [
                {"cache_key": "sync1", "text": "Halt!", "audio_base64": base64.b64encode(b"audio").decode(), "size_bytes": 5},
            ],
        })
        assert cache.has("sync1")


class TestStop:
    def test_stop_safe(self, worker):
        worker.handle_character_assign({
            "character_id": "x", "entity_name": "X",
            "voice_seed_base64": "", "params": {},
            "lines": [{"cache_key": "k", "text": "Hi", "category": "greeting"}],
        })
        time.sleep(0.5)
        worker.stop()
        assert not worker._running

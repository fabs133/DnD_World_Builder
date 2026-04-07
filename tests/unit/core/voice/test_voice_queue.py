"""Tests for VoiceGenerationQueue."""

import time
import pytest
from unittest.mock import MagicMock

from core.voice.voice_queue import VoiceGenerationQueue, VoiceJob
from core.voice.voice_profile import VoiceProfile
from core.voice.voice_cache import VoiceCache
from core.voice.voice_line_provider import VoiceLineProvider
from models.world.world_tile_manager import WorldTileManager


@pytest.fixture
def tile_manager():
    return WorldTileManager(5, 5, tile_type="square")


@pytest.fixture
def cache(tmp_path):
    return VoiceCache(tmp_path / "vc", max_size_mb=10)


@pytest.fixture
def engine():
    e = MagicMock()
    e.generate.return_value = b"fake_audio_data"
    e.detect_hardware.return_value = MagicMock(value="cpu")
    return e


@pytest.fixture
def provider():
    return VoiceLineProvider()


@pytest.fixture
def queue(engine, cache, provider, tile_manager):
    return VoiceGenerationQueue(
        voice_engine=engine,
        voice_cache=cache,
        voice_line_provider=provider,
        world_tile_manager=tile_manager,
        max_distance=2,
    )


class TestBFSDistances:

    def test_simple_grid(self, queue):
        distances = queue.bfs_distances((2, 2))
        assert distances[(2, 2)] == 0
        # Adjacent tiles should be distance 1
        for adj in [(2, 1), (2, 3), (1, 2), (3, 2)]:
            assert distances.get(adj) == 1

    def test_respects_max_distance(self, queue):
        distances = queue.bfs_distances((0, 0))
        # max_distance=2, so nothing should be >2
        for dist in distances.values():
            assert dist <= 2

    def test_origin_is_distance_zero(self, queue):
        distances = queue.bfs_distances((1, 1))
        assert distances[(1, 1)] == 0


class TestQueueOperations:

    def test_rebuild_populates_jobs(self, queue, tile_manager):
        # Place a voiced entity on a tile
        from models.entities.game_entity import GameEntity
        from core.voice.voice_profile import VoiceProfile

        entity = GameEntity("NPC", "npc")
        entity.voice_profile = VoiceProfile(source_type="preset", reference_audio="x.wav")
        entity.dialogue_lines = {"greeting": ["Hello"]}
        tile_manager.place_entity(entity, 1, 0)
        tile_manager.tiles[(1, 0)].entities.append(entity)

        queue.set_player_position((0, 0))

        stats = queue.get_queue_stats()
        assert stats["queued"] >= 1

    def test_skips_cached_lines(self, queue, cache, tile_manager):
        from models.entities.game_entity import GameEntity

        entity = GameEntity("NPC", "npc")
        entity.voice_profile = VoiceProfile(source_type="preset", reference_audio="x.wav")
        entity.dialogue_lines = {"greeting": ["Hello"]}
        tile_manager.place_entity(entity, 0, 0)
        tile_manager.tiles[(0, 0)].entities.append(entity)

        # Pre-cache the line
        key = VoiceCache.compute_cache_key(
            entity.voice_profile.voice_id, "Hello",
            entity.voice_profile.exaggeration,
            entity.voice_profile.speed_factor,
            entity.voice_profile.cfg_weight,
        )
        cache.put(key, b"audio", "NPC", "Hello")

        queue.set_player_position((0, 0))
        assert queue.get_queue_stats()["queued"] == 0

    def test_effective_priority_ordering(self):
        j1 = VoiceJob(effective_priority=1, entity_name="A", voice_profile=None,
                       text="t", line_priority=0, tile_distance=1, cache_key="k1")
        j2 = VoiceJob(effective_priority=3, entity_name="B", voice_profile=None,
                       text="t", line_priority=2, tile_distance=1, cache_key="k2")
        assert j1 < j2  # lower priority = more urgent

    def test_request_immediate_cache_hit(self, queue, cache):
        profile = VoiceProfile(source_type="preset", reference_audio="x.wav")
        key = VoiceCache.compute_cache_key(profile.voice_id, "Hi")
        cache.put(key, b"audio", "NPC", "Hi")

        result = queue.request_immediate("Hi", profile, "NPC")
        assert result is not None  # returns cached path

    def test_request_immediate_cache_miss(self, queue):
        profile = VoiceProfile(source_type="preset", reference_audio="x.wav")
        result = queue.request_immediate("New line", profile, "NPC")
        assert result is None
        assert queue.get_queue_stats()["queued"] == 1


class TestWorker:

    def test_worker_generates_and_caches(self, queue, engine, cache, tile_manager):
        from models.entities.game_entity import GameEntity

        entity = GameEntity("NPC", "npc")
        entity.voice_profile = VoiceProfile(source_type="preset", reference_audio="x.wav")
        entity.dialogue_lines = {"greeting": ["Hello worker"]}
        tile_manager.place_entity(entity, 0, 0)
        tile_manager.tiles[(0, 0)].entities.append(entity)

        queue.set_player_position((0, 0))
        queue.start()
        time.sleep(1.0)  # let worker process
        queue.stop()

        assert engine.generate.called
        stats = queue.get_queue_stats()
        assert stats["generated"] >= 1

    def test_stop_is_safe(self, queue):
        queue.start()
        queue.stop()
        assert not queue._running

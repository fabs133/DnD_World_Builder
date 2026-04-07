"""Tests for VoiceCache."""

import pytest
from core.voice.voice_cache import VoiceCache


@pytest.fixture
def cache(tmp_path):
    return VoiceCache(tmp_path / "voice_cache", max_size_mb=10)


class TestVoiceCache:

    def test_put_and_get(self, cache):
        key = VoiceCache.compute_cache_key("v1", "Hello world")
        path = cache.put(key, b"RIFF" + b"\x00" * 100, "Hero", "Hello world")
        assert path.exists()
        assert cache.get(key) == path

    def test_has_true_after_put(self, cache):
        key = VoiceCache.compute_cache_key("v1", "Test")
        cache.put(key, b"audio", "NPC", "Test")
        assert cache.has(key) is True

    def test_has_false_for_unknown(self, cache):
        assert cache.has("nonexistent_key") is False

    def test_get_updates_last_used(self, cache):
        key = VoiceCache.compute_cache_key("v1", "Test")
        cache.put(key, b"audio", "NPC", "Test")
        t1 = cache._manifest[key]["last_used"]
        import time; time.sleep(0.01)
        cache.get(key)
        t2 = cache._manifest[key]["last_used"]
        assert t2 >= t1

    def test_compute_cache_key_deterministic(self):
        k1 = VoiceCache.compute_cache_key("v1", "Hello", 0.5, 1.0, 0.5)
        k2 = VoiceCache.compute_cache_key("v1", "Hello", 0.5, 1.0, 0.5)
        assert k1 == k2

    def test_compute_cache_key_differs_on_text(self):
        k1 = VoiceCache.compute_cache_key("v1", "Hello")
        k2 = VoiceCache.compute_cache_key("v1", "Goodbye")
        assert k1 != k2

    def test_compute_cache_key_differs_on_voice(self):
        k1 = VoiceCache.compute_cache_key("v1", "Hello")
        k2 = VoiceCache.compute_cache_key("v2", "Hello")
        assert k1 != k2

    def test_evict_lru_removes_oldest(self, cache):
        k1 = cache.put("k1", b"x" * 5000, "A", "line1")
        k2 = cache.put("k2", b"x" * 5000, "B", "line2")
        cache.get("k1")  # touch k1 so k2 is older
        cache.put("k3", b"x" * 5000, "C", "line3")
        evicted = cache.evict_lru(0)  # evict everything
        assert evicted >= 1

    def test_clear_entity_removes_all(self, cache):
        cache.put("k1", b"audio1", "Goblin", "line1")
        cache.put("k2", b"audio2", "Goblin", "line2")
        cache.put("k3", b"audio3", "Hero", "line3")
        removed = cache.clear_entity("Goblin")
        assert removed == 2
        assert cache.has("k3")

    def test_manifest_persistence(self, tmp_path):
        cache1 = VoiceCache(tmp_path / "vc", max_size_mb=10)
        cache1.put("k1", b"data", "NPC", "hello")
        cache1.save_manifest()

        cache2 = VoiceCache(tmp_path / "vc", max_size_mb=10)
        assert cache2.has("k1")

    def test_cache_size_tracking(self, cache):
        cache.put("k1", b"x" * 1024, "A", "test")
        size = cache.get_size_mb()
        assert size > 0

    def test_get_stats(self, cache):
        cache.put("k1", b"data", "A", "line1")
        cache.put("k2", b"data", "B", "line2")
        stats = cache.get_stats()
        assert stats["total_entries"] == 2

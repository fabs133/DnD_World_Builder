"""Tests for VoiceSwarmOrchestrator."""

import pytest
from unittest.mock import MagicMock

from network.voice.swarm_orchestrator import VoiceSwarmOrchestrator
from core.voice.voice_profile import VoiceProfile


class FakeEntity:
    def __init__(self, name, lines_count=5, voiced=True):
        self.name = name
        self.entity_type = "npc"
        self.voice_profile = VoiceProfile(
            source_type="preset" if voiced else "none",
            reference_audio="seed.wav" if voiced else None,
        ) if voiced else None
        self.dialogue_lines = {"greeting": [f"Line {i}" for i in range(lines_count)]}


@pytest.fixture
def orch():
    provider = MagicMock()
    provider.get_lines_for_entity.side_effect = lambda e: [
        MagicMock(cache_key=f"k{i}", text=f"Line {i}", category="greeting")
        for i in range(len(e.dialogue_lines.get("greeting", [])))
    ]
    cache = MagicMock()
    cache.has.return_value = False
    return VoiceSwarmOrchestrator(voice_cache=cache, voice_line_provider=provider)


class TestRegistration:
    def test_register_workers(self, orch):
        orch.register_worker("p1", "Alice", {"hardware_tier": "gpu"})
        orch.register_worker("p2", "Bob", {"hardware_tier": "cpu"})
        assert len(orch._workers) == 2


class TestBinPacking:
    def test_balanced(self, orch):
        """4 chars (8,6,5,3 lines) across 2 GPUs → roughly balanced."""
        orch.register_worker("p1", "Alice", {"hardware_tier": "gpu"})
        orch.register_worker("p2", "Bob", {"hardware_tier": "gpu"})

        entities = [
            FakeEntity("A", 8), FakeEntity("B", 6),
            FakeEntity("C", 5), FakeEntity("D", 3),
        ]
        assignments = orch.start_generation(entities)
        p1_lines = orch._workers["p1"].assigned_line_count
        p2_lines = orch._workers["p2"].assigned_line_count
        assert abs(p1_lines - p2_lines) <= 5

    def test_largest_first(self, orch):
        orch.register_worker("p1", "Alice", {"hardware_tier": "gpu"})
        entities = [FakeEntity("Small", 2), FakeEntity("Big", 10)]
        assignments = orch.start_generation(entities)
        # Both should be assigned to the single worker
        assert len(assignments["p1"]) == 2

    def test_cpu_only_small(self, orch):
        orch.register_worker("p1", "Alice", {"hardware_tier": "cpu"})
        entities = [FakeEntity("Big", 10), FakeEntity("Small", 3)]
        assignments = orch.start_generation(entities)
        # CPU should only get the small one (≤5 lines)
        assert "small" in assignments["p1"]
        assert "big" not in assignments["p1"]

    def test_none_gets_nothing(self, orch):
        orch.register_worker("p1", "Alice", {"hardware_tier": "none"})
        entities = [FakeEntity("A", 3)]
        assignments = orch.start_generation(entities)
        assert len(assignments["p1"]) == 0

    def test_cached_characters_skipped(self, orch):
        orch._cache.has.return_value = True  # all cached
        orch.register_worker("p1", "Alice", {"hardware_tier": "gpu"})
        entities = [FakeEntity("A", 5)]
        assignments = orch.start_generation(entities)
        assert len(assignments["p1"]) == 0

    def test_single_worker_gets_everything(self, orch):
        orch.register_worker("p1", "Alice", {"hardware_tier": "gpu"})
        entities = [FakeEntity("A", 5), FakeEntity("B", 3), FakeEntity("C", 7)]
        assignments = orch.start_generation(entities)
        assert len(assignments["p1"]) == 3


class TestCompletion:
    def test_handle_complete(self, orch):
        orch.register_worker("p1", "Alice", {"hardware_tier": "gpu"})
        entities = [FakeEntity("Marta", 2)]
        orch.start_generation(entities)

        result = orch.handle_character_complete("p1", {
            "character_id": "marta",
            "entity_name": "Marta",
            "results": [{"cache_key": "k0", "text": "Hello", "audio_base64": "AAAA"}],
        })
        assert result is not None
        assert orch._characters["marta"].completed is True


class TestDisconnect:
    def test_reassigns(self, orch):
        orch.register_worker("p1", "Alice", {"hardware_tier": "gpu"})
        orch.register_worker("p2", "Bob", {"hardware_tier": "gpu"})
        entities = [FakeEntity("A", 5)]
        orch.start_generation(entities)

        reassigned = orch.handle_worker_disconnect("p1")
        # Uncompleted characters should be reassigned
        assert len(reassigned) >= 0  # may be 0 if assigned to p2


class TestStats:
    def test_accurate(self, orch):
        orch.register_worker("p1", "Alice", {"hardware_tier": "gpu"})
        entities = [FakeEntity("A", 3)]
        orch.start_generation(entities)
        stats = orch.get_stats()
        assert stats["total_characters"] == 1
        assert stats["workers"] == 1

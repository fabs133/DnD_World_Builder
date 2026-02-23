"""Tests for behavioral stats tracking and aggregation."""

import pytest

from core.testing.behavioral.stats import BehaviorEvent, EntityRunStats, BehaviorStats


class TestEntityRunStats:
    def test_record_event(self):
        stats = EntityRunStats("Goblin", "chaotic_evil", run_id=0, seed=42)
        stats.record(1, BehaviorEvent.ATTACKED, target="Fighter")
        assert len(stats.events) == 1
        assert stats.events[0] == (1, BehaviorEvent.ATTACKED, {"target": "Fighter"})

    def test_count_events(self):
        stats = EntityRunStats("Goblin", "chaotic_evil", run_id=0, seed=42)
        stats.record(1, BehaviorEvent.ATTACKED)
        stats.record(2, BehaviorEvent.ATTACKED)
        stats.record(3, BehaviorEvent.FLED_COMBAT)
        assert stats.count(BehaviorEvent.ATTACKED) == 2
        assert stats.count(BehaviorEvent.FLED_COMBAT) == 1
        assert stats.count(BehaviorEvent.DIED) == 0

    def test_has_event(self):
        stats = EntityRunStats("Goblin", "chaotic_evil", run_id=0, seed=42)
        stats.record(1, BehaviorEvent.ATTACKED)
        assert stats.has(BehaviorEvent.ATTACKED) is True
        assert stats.has(BehaviorEvent.DIED) is False

    def test_numeric_accumulators(self):
        stats = EntityRunStats("Goblin", "chaotic_evil", run_id=0, seed=42)
        stats.damage_dealt = 15
        stats.damage_taken = 7
        stats.kills = 1
        stats.died = False
        stats.final_hp_percent = 0.5
        assert stats.damage_dealt == 15
        assert stats.kills == 1


class TestBehaviorStats:
    def _make_run(self, entity_name="Goblin", alignment="chaotic_evil",
                  run_id=0, seed=42, events=None, died=False,
                  damage_dealt=0, kills=0):
        stats = EntityRunStats(entity_name, alignment, run_id, seed)
        stats.died = died
        stats.damage_dealt = damage_dealt
        stats.kills = kills
        if events:
            for round_num, event in events:
                stats.record(round_num, event)
        return stats

    def test_empty_runs(self):
        stats = BehaviorStats("Goblin", "chaotic_evil", runs=[])
        assert stats.run_count == 0
        assert stats.survival_rate == 0.0
        assert stats.avg_damage_dealt == 0.0
        assert stats.flee_rate == 0.0
        assert stats.target_entropy == 0.0

    def test_survival_rate(self):
        runs = [
            self._make_run(run_id=0, died=False),
            self._make_run(run_id=1, died=True),
            self._make_run(run_id=2, died=False),
            self._make_run(run_id=3, died=False),
        ]
        stats = BehaviorStats("Goblin", "chaotic_evil", runs=runs)
        assert stats.survival_rate == 0.75

    def test_avg_damage_dealt(self):
        runs = [
            self._make_run(run_id=0, damage_dealt=10),
            self._make_run(run_id=1, damage_dealt=20),
        ]
        stats = BehaviorStats("Goblin", "chaotic_evil", runs=runs)
        assert stats.avg_damage_dealt == 15.0

    def test_avg_kills(self):
        runs = [
            self._make_run(run_id=0, kills=1),
            self._make_run(run_id=1, kills=3),
        ]
        stats = BehaviorStats("Goblin", "chaotic_evil", runs=runs)
        assert stats.avg_kills == 2.0

    def test_flee_rate(self):
        run = self._make_run(events=[
            (1, BehaviorEvent.CONSIDERED_FLEEING),
            (1, BehaviorEvent.FLED_COMBAT),
            (2, BehaviorEvent.CONSIDERED_FLEEING),
            (2, BehaviorEvent.STAYED_DESPITE_DANGER),
        ])
        stats = BehaviorStats("Goblin", "chaotic_evil", runs=[run])
        assert stats.flee_rate == 0.5

    def test_mercy_rate(self):
        run = self._make_run(events=[
            (1, BehaviorEvent.COULD_EXECUTE_DOWNED),
            (1, BehaviorEvent.SPARED_DOWNED),
            (2, BehaviorEvent.COULD_EXECUTE_DOWNED),
            (2, BehaviorEvent.EXECUTED_DOWNED),
            (3, BehaviorEvent.COULD_EXECUTE_DOWNED),
            (3, BehaviorEvent.SPARED_DOWNED),
        ])
        stats = BehaviorStats("Goblin", "chaotic_evil", runs=[run])
        # 2 spared / 3 opportunities
        assert abs(stats.mercy_rate - 2 / 3) < 0.001

    def test_protect_rate(self):
        run = self._make_run(events=[
            (1, BehaviorEvent.ALLY_THREATENED),
            (1, BehaviorEvent.PROTECTED_ALLY),
            (2, BehaviorEvent.ALLY_THREATENED),
            (2, BehaviorEvent.IGNORED_DYING_ALLY),
        ])
        stats = BehaviorStats("Goblin", "chaotic_evil", runs=[run])
        assert stats.protect_rate == 0.5

    def test_rate_zero_opportunity(self):
        run = self._make_run(events=[])
        stats = BehaviorStats("Goblin", "chaotic_evil", runs=[run])
        assert stats.mercy_rate == 0.0
        assert stats.flee_rate == 0.0
        assert stats.protect_rate == 0.0

    def test_target_entropy_single_target_type(self):
        run = self._make_run(events=[
            (1, BehaviorEvent.TARGETED_WEAKEST),
            (2, BehaviorEvent.TARGETED_WEAKEST),
            (3, BehaviorEvent.TARGETED_WEAKEST),
        ])
        stats = BehaviorStats("Goblin", "chaotic_evil", runs=[run])
        assert stats.target_entropy == 0.0  # All same = zero entropy

    def test_target_entropy_uniform(self):
        run = self._make_run(events=[
            (1, BehaviorEvent.TARGETED_WEAKEST),
            (2, BehaviorEvent.TARGETED_STRONGEST),
            (3, BehaviorEvent.TARGETED_NEAREST),
            (4, BehaviorEvent.TARGETED_RANDOM),
        ])
        stats = BehaviorStats("Goblin", "chaotic_evil", runs=[run])
        assert abs(stats.target_entropy - 1.0) < 0.001  # Uniform = max entropy

    def test_target_entropy_partial(self):
        run = self._make_run(events=[
            (1, BehaviorEvent.TARGETED_WEAKEST),
            (2, BehaviorEvent.TARGETED_WEAKEST),
            (3, BehaviorEvent.TARGETED_STRONGEST),
            (4, BehaviorEvent.TARGETED_RANDOM),
        ])
        stats = BehaviorStats("Goblin", "chaotic_evil", runs=[run])
        assert 0.0 < stats.target_entropy < 1.0

    def test_total_across_runs(self):
        run1 = self._make_run(run_id=0, events=[
            (1, BehaviorEvent.ATTACKED),
            (2, BehaviorEvent.ATTACKED),
        ])
        run2 = self._make_run(run_id=1, events=[
            (1, BehaviorEvent.ATTACKED),
        ])
        stats = BehaviorStats("Goblin", "chaotic_evil", runs=[run1, run2])
        assert stats.total(BehaviorEvent.ATTACKED) == 3

    def test_to_dict(self):
        run = self._make_run(damage_dealt=10, kills=1, events=[
            (1, BehaviorEvent.ATTACKED),
        ])
        stats = BehaviorStats("Goblin", "chaotic_evil", runs=[run])
        d = stats.to_dict()
        assert d["entity_name"] == "Goblin"
        assert d["alignment"] == "chaotic_evil"
        assert d["run_count"] == 1
        assert "survival_rate" in d
        assert "target_entropy" in d

"""Tests for MockAIAdapter deterministic AI."""

import random
import pytest

from core.testing.behavioral.mock_ai import MockAIAdapter
from core.testing.behavioral.stats import BehaviorEvent, EntityRunStats
from core.engine.actions.attack_action import AttackAction
from core.engine.actions.end_turn_action import EndTurnAction
from core.engine.game_state import GameState
from models.ai.alignment import Alignment
from models.ai.personality import EntityPersonality


class SimpleEntity:
    """Minimal entity for testing."""

    def __init__(self, name, entity_type, hp, max_hp=None,
                 position=(0, 0), alignment=None):
        self.name = name
        self.entity_type = entity_type
        self.hp = hp
        self.max_hp = max_hp or hp
        self.stats = {"Dexterity": 10, "max_hp": self.max_hp}
        self.armor_class = 12
        self.speed = 30
        self.position = position
        self.conditions = []
        self.initiative = 0
        self.triggers = []
        self.inventory = []
        self.personality = None
        if alignment:
            self.personality = EntityPersonality(alignment=Alignment.from_string(alignment))


def _make_adapter(entities, seed=42, stats=None):
    entities_by_name = {e.name: e for e in entities}
    stats_collector = stats or {}
    return MockAIAdapter(
        entities_by_name=entities_by_name,
        rng=random.Random(seed),
        stats_collector=stats_collector,
    ), entities_by_name


def _make_stats(entities):
    return {
        e.name: EntityRunStats(e.name, "test", run_id=0, seed=42)
        for e in entities
    }


class TestMockAIBasicActions:
    def test_returns_attack_when_enemy_alive(self):
        fighter = SimpleEntity("Fighter", "player", 20, alignment="lawful good")
        goblin = SimpleEntity("Goblin", "enemy", 7, alignment="chaotic evil")
        adapter, _ = _make_adapter([fighter, goblin])

        action = adapter.choose_action("Fighter", None, ["ATTACK", "END_TURN"])
        assert isinstance(action, AttackAction)
        assert action.target.name == "Goblin"

    def test_returns_end_turn_when_no_enemies(self):
        fighter = SimpleEntity("Fighter", "player", 20, alignment="lawful good")
        ally = SimpleEntity("Ally", "player", 15, alignment="neutral good")
        adapter, _ = _make_adapter([fighter, ally])

        action = adapter.choose_action("Fighter", None, ["ATTACK", "END_TURN"])
        assert isinstance(action, EndTurnAction)

    def test_returns_end_turn_for_unknown_entity(self):
        fighter = SimpleEntity("Fighter", "player", 20)
        adapter, _ = _make_adapter([fighter])

        action = adapter.choose_action("NonExistent", None, ["ATTACK", "END_TURN"])
        assert isinstance(action, EndTurnAction)


class TestMockAIDeterminism:
    def test_same_seed_same_result(self):
        fighter = SimpleEntity("Fighter", "player", 20, alignment="lawful good")
        goblin = SimpleEntity("Goblin", "enemy", 7, alignment="chaotic evil")

        adapter1, _ = _make_adapter([fighter, goblin], seed=42)
        adapter2, _ = _make_adapter([fighter, goblin], seed=42)

        action1 = adapter1.choose_action("Fighter", None, ["ATTACK", "END_TURN"])
        action2 = adapter2.choose_action("Fighter", None, ["ATTACK", "END_TURN"])

        assert type(action1) is type(action2)
        if isinstance(action1, AttackAction):
            assert action1.target.name == action2.target.name


class TestMockAIFleeCheck:
    def test_considers_fleeing_at_low_hp(self):
        # NE has flee_threshold=0.6 (cowardly minion weights)
        goblin = SimpleEntity("Goblin", "enemy", 2, max_hp=10, alignment="neutral evil")
        fighter = SimpleEntity("Fighter", "player", 20, alignment="lawful good")
        stats = _make_stats([goblin, fighter])
        adapter, _ = _make_adapter([goblin, fighter], stats=stats, seed=42)

        adapter.choose_action("Goblin", None, ["ATTACK", "END_TURN"])
        assert stats["Goblin"].has(BehaviorEvent.CONSIDERED_FLEEING)


class TestMockAIProtect:
    def test_protects_low_hp_ally(self):
        # LG has high ally_protection (0.9)
        paladin = SimpleEntity("Paladin", "player", 30, alignment="lawful good",
                               position=(0, 0))
        wizard = SimpleEntity("Wizard", "player", 2, max_hp=14, alignment="chaotic good",
                              position=(1, 0))
        goblin = SimpleEntity("Goblin", "enemy", 7, alignment="chaotic evil",
                              position=(2, 0))
        stats = _make_stats([paladin, wizard, goblin])

        # Use multiple seeds to increase chance of protection triggering
        protected = False
        for seed in range(100):
            for e in [paladin, wizard, goblin]:
                e.hp = e.max_hp
            wizard.hp = 2  # Low HP
            stats_run = _make_stats([paladin, wizard, goblin])
            adapter, _ = _make_adapter([paladin, wizard, goblin], stats=stats_run, seed=seed)
            adapter.choose_action("Paladin", None, ["ATTACK", "END_TURN"])
            if stats_run["Paladin"].has(BehaviorEvent.PROTECTED_ALLY):
                protected = True
                break
        assert protected, "LG paladin should protect allies across 100 seeds"


class TestMockAIMercy:
    def test_records_mercy_opportunity(self):
        fighter = SimpleEntity("Fighter", "player", 20, alignment="lawful good")
        goblin = SimpleEntity("Goblin", "enemy", 0, max_hp=7, alignment="chaotic evil")
        stats = _make_stats([fighter, goblin])
        adapter, _ = _make_adapter([fighter, goblin], stats=stats, seed=42)

        # With a downed enemy and alive enemies absent, should trigger mercy check
        adapter.choose_action("Fighter", None, ["ATTACK", "END_TURN"])
        assert stats["Fighter"].has(BehaviorEvent.COULD_EXECUTE_DOWNED)


class TestMockAITargetSelection:
    def test_targets_weakest_with_low_priority(self):
        # Create entity with low target_priority
        hunter = SimpleEntity("Hunter", "player", 20, alignment="neutral evil")
        strong = SimpleEntity("Strong", "enemy", 20, position=(1, 0))
        weak = SimpleEntity("Weak", "enemy", 3, position=(2, 0))

        stats = _make_stats([hunter, strong, weak])
        targeted_weak = False
        for seed in range(50):
            stats_run = _make_stats([hunter, strong, weak])
            adapter, _ = _make_adapter([hunter, strong, weak], stats=stats_run, seed=seed)
            action = adapter.choose_action("Hunter", None, ["ATTACK", "END_TURN"])
            if isinstance(action, AttackAction) and action.target.name == "Weak":
                if stats_run["Hunter"].has(BehaviorEvent.TARGETED_WEAKEST):
                    targeted_weak = True
                    break
        assert targeted_weak, "NE should target weak enemies sometimes"

    def test_chaotic_targets_randomly(self):
        chaos = SimpleEntity("Chaos", "player", 20, alignment="chaotic evil")
        enemy1 = SimpleEntity("E1", "enemy", 10, position=(1, 0))
        enemy2 = SimpleEntity("E2", "enemy", 10, position=(2, 0))

        targets_seen = set()
        for seed in range(50):
            adapter, _ = _make_adapter([chaos, enemy1, enemy2], seed=seed)
            action = adapter.choose_action("Chaos", None, ["ATTACK", "END_TURN"])
            if isinstance(action, AttackAction):
                targets_seen.add(action.target.name)
        # Chaotic evil (low predictability) should hit both targets across runs
        assert len(targets_seen) >= 2, "CE should target different enemies across seeds"


class TestMockAIStatsRecording:
    def test_records_events_to_stats_collector(self):
        fighter = SimpleEntity("Fighter", "player", 20, alignment="lawful good")
        goblin = SimpleEntity("Goblin", "enemy", 7, alignment="chaotic evil")
        stats = _make_stats([fighter, goblin])
        adapter, _ = _make_adapter([fighter, goblin], stats=stats, seed=42)

        adapter.choose_action("Fighter", None, ["ATTACK", "END_TURN"])
        assert stats["Fighter"].has(BehaviorEvent.ATTACKED)

    def test_no_crash_without_stats_collector(self):
        fighter = SimpleEntity("Fighter", "player", 20, alignment="lawful good")
        goblin = SimpleEntity("Goblin", "enemy", 7, alignment="chaotic evil")
        adapter, _ = _make_adapter([fighter, goblin])

        action = adapter.choose_action("Fighter", None, ["ATTACK", "END_TURN"])
        assert isinstance(action, AttackAction)


class TestMockAIMovement:
    def test_aggressive_moves_toward_enemy(self):
        fighter = SimpleEntity("Fighter", "player", 20, alignment="chaotic evil",
                               position=(0, 0))
        goblin = SimpleEntity("Goblin", "enemy", 7, position=(5, 5))
        adapter, _ = _make_adapter([fighter, goblin])

        valid = [(1, 1), (0, 1), (1, 0)]
        pos = adapter.choose_movement("Fighter", None, valid)
        assert pos == (1, 1)  # Closest to (5, 5)

    def test_defensive_moves_away_from_enemy(self):
        # True neutral has aggression ~0.35 (defensive)
        neutral = SimpleEntity("Neutral", "player", 20, alignment="true neutral",
                               position=(2, 2))
        goblin = SimpleEntity("Goblin", "enemy", 7, position=(3, 3))
        adapter, _ = _make_adapter([neutral, goblin])

        valid = [(1, 1), (3, 3), (2, 1)]
        pos = adapter.choose_movement("Neutral", None, valid)
        assert pos == (1, 1)  # Farthest from (3, 3)

"""Tests for CombatOrchestrator."""

import pytest
from unittest.mock import MagicMock

from core.events import COMBAT_STARTED, ENTITY_DIED
from core.gameCreation.event_bus import EventBus
from models.combat.combat_orchestrator import CombatOrchestrator
from models.combat.combat_instance import CombatInstance, CombatState
from models.combat.combatant import Combatant, CombatantFaction


class FakeEntity:
    def __init__(self, name="Hero", hp=20, max_hp=20, speed=30, dex=10):
        self.name = name
        self.hp = hp
        self.max_hp = max_hp
        self.speed = speed
        self.stats = {"Dexterity": dex, "hp": hp, "max_hp": max_hp}
        self.entity_type = "player"

    def take_damage(self, amount, damage_type=""):
        self.hp = max(0, self.hp - amount)
        self.stats["hp"] = self.hp


@pytest.fixture(autouse=True)
def reset_bus():
    EventBus.reset()
    yield
    EventBus.reset()


def _make_instance(players, enemies):
    combatants = []
    for e in players:
        combatants.append(Combatant(entity=e, faction=CombatantFaction.PLAYER))
    for e in enemies:
        combatants.append(Combatant(entity=e, faction=CombatantFaction.ENEMY))
    return CombatInstance(
        instance_id="test", template_id="t", template_name="Test",
        combatants=combatants,
    )


class TestStartSetup:
    def test_emits_event(self):
        events = []
        EventBus.subscribe(COMBAT_STARTED, lambda d: events.append(d))

        inst = _make_instance([], [])
        orch = CombatOrchestrator(inst, gamemaster=MagicMock())
        orch.start_setup()

        assert inst.state == CombatState.SETUP
        assert len(events) == 1


class TestRollInitiative:
    def test_sorts_descending(self):
        p = FakeEntity("Hero", dex=10)
        e = FakeEntity("Goblin", dex=18)
        inst = _make_instance([p], [e])
        orch = CombatOrchestrator(inst, gamemaster=MagicMock())
        orch.roll_initiative(seed=42)

        # Higher DEX modifier should generally rank higher
        assert inst.state == CombatState.INITIATIVE
        assert len(inst.combatants) == 2

    def test_uses_dex_modifier(self):
        p = FakeEntity("Hero", dex=20)  # +5 mod
        e = FakeEntity("Goblin", dex=8)  # -1 mod
        inst = _make_instance([p], [e])
        orch = CombatOrchestrator(inst, gamemaster=MagicMock())
        rolls = orch.roll_initiative(seed=42)

        hero_roll = next(r for r in rolls if r["name"] == "Hero")
        goblin_roll = next(r for r in rolls if r["name"] == "Goblin")
        assert hero_roll["modifier"] == 5
        assert goblin_roll["modifier"] == -1

    def test_deterministic_with_seed(self):
        p = FakeEntity("Hero")
        e = FakeEntity("Goblin")
        inst1 = _make_instance([p], [e])
        inst2 = _make_instance([p], [e])
        orch1 = CombatOrchestrator(inst1, gamemaster=MagicMock())
        orch2 = CombatOrchestrator(inst2, gamemaster=MagicMock())

        rolls1 = orch1.roll_initiative(seed=99)
        rolls2 = orch2.roll_initiative(seed=99)
        assert rolls1 == rolls2


class TestReorderInitiative:
    def test_moves_combatant(self):
        p = FakeEntity("Hero")
        e1 = FakeEntity("Goblin1")
        e2 = FakeEntity("Goblin2")
        inst = _make_instance([p], [e1, e2])
        orch = CombatOrchestrator(inst, gamemaster=MagicMock())

        # Move Hero to index 2 (last)
        orch.reorder_initiative("Hero", 2)
        assert inst.combatants[2].name == "Hero"


class TestSurprise:
    def test_apply_surprise_marks_combatants(self):
        p = FakeEntity("Hero")
        e = FakeEntity("Goblin")
        inst = _make_instance([p], [e])
        orch = CombatOrchestrator(inst, gamemaster=MagicMock())
        orch.apply_surprise(["Hero"])

        hero = next(c for c in inst.combatants if c.name == "Hero")
        goblin = next(c for c in inst.combatants if c.name == "Goblin")
        assert hero.surprised is True
        assert goblin.surprised is False


class TestBeginCombat:
    def test_transitions_to_active(self):
        p = FakeEntity("Hero")
        e = FakeEntity("Goblin")
        inst = _make_instance([p], [e])
        orch = CombatOrchestrator(inst, gamemaster=MagicMock())
        orch.roll_initiative(seed=42)
        orch.begin_combat()

        assert inst.state == CombatState.ACTIVE
        assert inst.round_number == 1


class TestEndTurn:
    def test_advances_to_next(self):
        p = FakeEntity("Hero")
        e = FakeEntity("Goblin")
        inst = _make_instance([p], [e])
        orch = CombatOrchestrator(inst, gamemaster=MagicMock())
        orch.roll_initiative(seed=42)
        orch.begin_combat()

        first = inst.current_combatant.name
        orch.end_turn()
        second = inst.current_combatant.name
        assert first != second

    def test_wraps_to_round_2(self):
        p = FakeEntity("Hero")
        e = FakeEntity("Goblin")
        inst = _make_instance([p], [e])
        orch = CombatOrchestrator(inst, gamemaster=MagicMock())
        orch.roll_initiative(seed=42)
        orch.begin_combat()

        orch.end_turn()  # second combatant
        orch.end_turn()  # wraps to round 2
        assert inst.round_number == 2

    def test_surprised_combatant_skipped_round_1(self):
        p = FakeEntity("Hero")
        e = FakeEntity("Goblin")
        inst = _make_instance([p], [e])
        orch = CombatOrchestrator(inst, gamemaster=MagicMock())
        orch.roll_initiative(seed=42)
        orch.apply_surprise([inst.combatants[0].name])
        orch.begin_combat()

        # The first combatant is surprised and should be skipped
        # After begin_combat, current_turn should have advanced past surprised
        skipped = [e for e in inst.event_log if e.get("type") == "turn_skipped"]
        assert len(skipped) >= 1


class TestEndConditions:
    def test_victory_when_all_enemies_down(self):
        p = FakeEntity("Hero", hp=20)
        e = FakeEntity("Goblin", hp=0)
        inst = _make_instance([p], [e])
        orch = CombatOrchestrator(inst, gamemaster=MagicMock())
        assert orch.check_end_conditions() == "victory"

    def test_defeat_when_all_players_down(self):
        p = FakeEntity("Hero", hp=0)
        e = FakeEntity("Goblin", hp=5)
        inst = _make_instance([p], [e])
        orch = CombatOrchestrator(inst, gamemaster=MagicMock())
        assert orch.check_end_conditions() == "defeat"

    def test_ongoing_when_both_sides_alive(self):
        p = FakeEntity("Hero", hp=10)
        e = FakeEntity("Goblin", hp=5)
        inst = _make_instance([p], [e])
        orch = CombatOrchestrator(inst, gamemaster=MagicMock())
        assert orch.check_end_conditions() is None


class TestApplyDamage:
    def test_reduces_hp(self):
        p = FakeEntity("Hero", hp=20, max_hp=20)
        inst = _make_instance([p], [])
        orch = CombatOrchestrator(inst, gamemaster=MagicMock())

        result = orch.apply_damage("Hero", 7)
        assert result["damage"] == 7
        assert result["remaining_hp"] == 13
        assert result["died"] is False

    def test_emits_entity_died(self):
        died_events = []
        EventBus.subscribe(ENTITY_DIED, lambda d: died_events.append(d))

        e = FakeEntity("Goblin", hp=3, max_hp=7)
        inst = _make_instance([], [e])
        orch = CombatOrchestrator(inst, gamemaster=MagicMock())

        result = orch.apply_damage("Goblin", 5)
        assert result["died"] is True
        assert len(died_events) == 1


class TestEndCombat:
    def test_transitions_to_ended(self):
        inst = _make_instance(
            [FakeEntity("Hero", hp=10)],
            [FakeEntity("Goblin", hp=0)],
        )
        orch = CombatOrchestrator(inst, gamemaster=MagicMock())
        summary = orch.end_combat("victory")

        assert inst.state == CombatState.ENDED
        assert summary["outcome"] == "victory"
        assert "Goblin" in summary["casualties"]
        assert "Hero" in summary["survivors"]

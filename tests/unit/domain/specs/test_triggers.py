"""Tests for domain.specs.triggers — Trigger system specs."""

import pytest

from domain.specs.base import AlwaysTrue, AlwaysFalse
from domain.specs.triggers import (
    EventType,
    TriggerEvent,
    ReactionResult,
    TriggerEvaluation,
    TriggerSpec,
    TriggerEvaluator,
    perception_trap,
    enter_zone_trigger,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

class FakeEntity:
    def __init__(self, entity_type="player", conditions=None, skill_modifiers=None):
        self.entity_type = entity_type
        self.conditions = conditions or []
        self.skill_modifiers = skill_modifiers or {}


# ── TriggerEvent ─────────────────────────────────────────────────────────────

class TestTriggerEvent:
    def test_create_with_enum(self):
        event = TriggerEvent(event_type=EventType.ENTER_TILE, source_entity_id="player1")
        assert event.event_type == EventType.ENTER_TILE

    def test_to_dict(self):
        event = TriggerEvent(
            event_type=EventType.TAKE_DAMAGE,
            source_entity_id="goblin",
            target_tile_id="tile_3_2",
            data={"amount": 5},
        )
        d = event.to_dict()
        assert d["event_type"] == "take_damage"
        assert d["source_entity_id"] == "goblin"
        assert d["data"]["amount"] == 5


# ── ReactionResult ───────────────────────────────────────────────────────────

class TestReactionResult:
    def test_to_dict(self):
        rr = ReactionResult(
            success=True,
            description="Trap sprung!",
            damage_dealt=10,
            conditions_applied=["poisoned"],
        )
        d = rr.to_dict()
        assert d["success"] is True
        assert d["damage_dealt"] == 10
        assert "poisoned" in d["conditions_applied"]


# ── TriggerEvaluation ────────────────────────────────────────────────────────

class TestTriggerEvaluation:
    def test_all_passed(self):
        from domain.specs.base import SpecResult
        results = [
            SpecResult(rule_id="a", passed=True),
            SpecResult(rule_id="b", passed=True),
        ]
        te = TriggerEvaluation(
            trigger_id="t1",
            event=TriggerEvent(EventType.ENTER_TILE),
            spec_results=results,
            fired=True,
        )
        assert te.all_passed is True
        assert len(te.failed_specs) == 0

    def test_failed_specs(self):
        from domain.specs.base import SpecResult
        results = [
            SpecResult(rule_id="a", passed=True),
            SpecResult(rule_id="b", passed=False),
        ]
        te = TriggerEvaluation(
            trigger_id="t1",
            event=TriggerEvent(EventType.ENTER_TILE),
            spec_results=results,
            fired=False,
        )
        assert te.all_passed is False
        assert len(te.failed_specs) == 1


# ── TriggerSpec ──────────────────────────────────────────────────────────────

class TestTriggerSpec:
    def test_fires_when_all_specs_pass(self):
        trigger = TriggerSpec(
            trigger_id="test_trigger",
            event_type=EventType.ENTER_TILE,
            pre_specs=[AlwaysTrue()],
        )
        event = TriggerEvent(EventType.ENTER_TILE)
        result = trigger.evaluate(event, FakeEntity())
        assert result.fired is True

    def test_does_not_fire_when_spec_fails(self):
        trigger = TriggerSpec(
            trigger_id="test_trigger",
            event_type=EventType.ENTER_TILE,
            pre_specs=[AlwaysFalse()],
        )
        event = TriggerEvent(EventType.ENTER_TILE)
        result = trigger.evaluate(event, FakeEntity())
        assert result.fired is False

    def test_reaction_called_on_fire(self):
        called = []
        trigger = TriggerSpec(
            trigger_id="test",
            event_type=EventType.ENTER_TILE,
            pre_specs=[AlwaysTrue()],
            reaction=lambda entity, ctx: (
                called.append(True) or
                ReactionResult(success=True, description="boom")
            ),
        )
        event = TriggerEvent(EventType.ENTER_TILE)
        result = trigger.evaluate(event, FakeEntity())
        assert result.fired is True
        assert len(called) == 1
        assert result.reaction_result.description == "boom"

    def test_cooldown_blocks_after_fire(self):
        trigger = TriggerSpec(
            trigger_id="cd_trigger",
            event_type=EventType.ENTER_TILE,
            pre_specs=[AlwaysTrue()],
            reaction=lambda e, c: ReactionResult(success=True, description="x"),
            cooldown_turns=2,
        )
        event = TriggerEvent(EventType.ENTER_TILE)
        entity = FakeEntity()

        # First fire
        r1 = trigger.evaluate(event, entity)
        assert r1.fired is True

        # Should be on cooldown
        r2 = trigger.evaluate(event, entity)
        assert r2.fired is False
        assert "cooldown" in r2.spec_results[0].message.lower()

    def test_advance_cooldown(self):
        trigger = TriggerSpec(
            trigger_id="cd",
            event_type=EventType.ENTER_TILE,
            pre_specs=[AlwaysTrue()],
            reaction=lambda e, c: ReactionResult(success=True, description="x"),
            cooldown_turns=1,
        )
        event = TriggerEvent(EventType.ENTER_TILE)
        entity = FakeEntity()

        trigger.evaluate(event, entity)
        trigger.advance_cooldown()
        r = trigger.evaluate(event, entity)
        assert r.fired is True

    def test_reset_cooldown(self):
        trigger = TriggerSpec(
            trigger_id="cd",
            event_type=EventType.ENTER_TILE,
            pre_specs=[AlwaysTrue()],
            reaction=lambda e, c: ReactionResult(success=True, description="x"),
            cooldown_turns=5,
        )
        event = TriggerEvent(EventType.ENTER_TILE)
        entity = FakeEntity()

        trigger.evaluate(event, entity)
        trigger.reset_cooldown()
        r = trigger.evaluate(event, entity)
        assert r.fired is True

    def test_chained_trigger(self):
        chain = TriggerSpec(
            trigger_id="chain",
            event_type=EventType.ENTER_TILE,
            pre_specs=[AlwaysTrue()],
            reaction=lambda e, c: ReactionResult(success=True, description="chained"),
        )
        trigger = TriggerSpec(
            trigger_id="main",
            event_type=EventType.ENTER_TILE,
            pre_specs=[AlwaysTrue()],
            reaction=lambda e, c: ReactionResult(success=True, description="main"),
            next_trigger=chain,
        )
        event = TriggerEvent(EventType.ENTER_TILE)
        result = trigger.evaluate(event, FakeEntity())
        assert result.fired is True
        assert len(result.chain_evaluations) == 1
        assert result.chain_evaluations[0].fired is True

    def test_to_dict(self):
        trigger = TriggerSpec(
            trigger_id="t1",
            event_type=EventType.ENTER_TILE,
            pre_specs=[AlwaysTrue()],
            label="Test Trigger",
            description="A test",
        )
        d = trigger.to_dict()
        assert d["trigger_id"] == "t1"
        assert d["event_type"] == "enter_tile"
        assert d["label"] == "Test Trigger"


# ── TriggerEvaluator ────────────────────────────────────────────────────────

class TestTriggerEvaluator:
    def test_register_and_evaluate(self):
        evaluator = TriggerEvaluator()
        trigger = TriggerSpec(
            trigger_id="t1",
            event_type=EventType.ENTER_TILE,
            pre_specs=[AlwaysTrue()],
        )
        evaluator.register(trigger)
        event = TriggerEvent(EventType.ENTER_TILE)
        results = evaluator.evaluate_all(event, FakeEntity())
        assert len(results) == 1
        assert results[0].fired is True

    def test_unregister(self):
        evaluator = TriggerEvaluator()
        trigger = TriggerSpec(trigger_id="t1", event_type=EventType.ENTER_TILE)
        evaluator.register(trigger)
        evaluator.unregister("t1")
        assert evaluator.get("t1") is None

    def test_evaluate_fired_only(self):
        evaluator = TriggerEvaluator()
        evaluator.register(TriggerSpec("fires", EventType.ENTER_TILE, pre_specs=[AlwaysTrue()]))
        evaluator.register(TriggerSpec("no_fire", EventType.ENTER_TILE, pre_specs=[AlwaysFalse()]))
        event = TriggerEvent(EventType.ENTER_TILE)
        fired = evaluator.evaluate_fired_only(event, FakeEntity())
        assert len(fired) == 1
        assert fired[0].trigger_id == "fires"

    def test_evaluate_wrong_event_type(self):
        evaluator = TriggerEvaluator()
        evaluator.register(TriggerSpec("t1", EventType.ENTER_TILE, pre_specs=[AlwaysTrue()]))
        event = TriggerEvent(EventType.TAKE_DAMAGE)
        results = evaluator.evaluate_all(event, FakeEntity())
        assert len(results) == 0

    def test_advance_all_cooldowns(self):
        evaluator = TriggerEvaluator()
        t = TriggerSpec(
            "cd", EventType.ENTER_TILE,
            pre_specs=[AlwaysTrue()],
            reaction=lambda e, c: ReactionResult(success=True, description="x"),
            cooldown_turns=1,
        )
        evaluator.register(t)

        event = TriggerEvent(EventType.ENTER_TILE)
        entity = FakeEntity()
        evaluator.evaluate_all(event, entity)  # fires, enters cooldown
        evaluator.advance_all_cooldowns()
        results = evaluator.evaluate_all(event, entity)
        assert results[0].fired is True  # cooldown expired

    def test_to_dict(self):
        evaluator = TriggerEvaluator()
        evaluator.register(TriggerSpec("t1", EventType.START_TURN))
        d = evaluator.to_dict()
        assert "t1" in d["triggers"]


# ── Factory functions ────────────────────────────────────────────────────────

class TestPerceptionTrap:
    def test_fires_on_failed_check(self):
        trap = perception_trap("pit_trap", perception_dc=15, damage=10)
        entity = FakeEntity(entity_type="player", skill_modifiers={"Perception": 0})
        event = TriggerEvent(EventType.ENTER_TILE)
        ctx = {"roll": 5}  # 5 + 0 = 5 < 15 → fails → inverted → fires
        result = trap.evaluate(event, entity, ctx)
        assert result.fired is True
        assert result.reaction_result.damage_dealt == 10

    def test_does_not_fire_on_passed_check(self):
        trap = perception_trap("pit_trap", perception_dc=10, damage=10)
        entity = FakeEntity(entity_type="player", skill_modifiers={"Perception": 5})
        event = TriggerEvent(EventType.ENTER_TILE)
        ctx = {"roll": 15}  # 15 + 5 = 20 >= 10 → passes → inverted → NOT fires
        result = trap.evaluate(event, entity, ctx)
        assert result.fired is False


class TestEnterZoneTrigger:
    def test_always_fires(self):
        zone = enter_zone_trigger("zone1", "healing", "You feel warm")
        event = TriggerEvent(EventType.ENTER_TILE)
        result = zone.evaluate(event, FakeEntity())
        assert result.fired is True
        assert result.reaction_result.success is True

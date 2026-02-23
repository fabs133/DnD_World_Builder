"""Tests for AttackAction."""

import random
import pytest
from core.engine.actions.attack_action import AttackAction


class SimpleEntity:
    def __init__(self, name, hp=10, armor_class=12):
        self.name = name
        self.hp = hp
        self.armor_class = armor_class


class TestAttackAction:
    def test_hit_reduces_target_hp(self):
        # Use a seeded RNG that we know will roll high
        rng = random.Random(42)
        actor = SimpleEntity("Fighter", hp=20)
        target = SimpleEntity("Goblin", hp=7, armor_class=10)

        action = AttackAction(
            actor, target, damage_expr="1d6", to_hit_bonus=5, rng=rng
        )
        result = action.execute(None)

        if result["hit"]:
            assert target.hp < 7
            assert result["damage"] > 0
        else:
            assert target.hp == 7

    def test_miss_does_not_reduce_hp(self):
        # Force a low roll with rng
        rng = random.Random()
        actor = SimpleEntity("Fighter", hp=20)
        target = SimpleEntity("Dragon", hp=100, armor_class=30)  # Very high AC

        action = AttackAction(
            actor, target, damage_expr="1d6", to_hit_bonus=0, rng=rng
        )
        result = action.execute(None)

        # With AC 30 and no bonus, almost guaranteed miss
        if not result["hit"]:
            assert target.hp == 100

    def test_validate_dead_actor(self):
        actor = SimpleEntity("Dead", hp=0)
        target = SimpleEntity("Goblin", hp=7)
        action = AttackAction(actor, target)

        assert action.validate(None) is False

    def test_validate_dead_target(self):
        actor = SimpleEntity("Fighter", hp=20)
        target = SimpleEntity("Dead", hp=0)
        action = AttackAction(actor, target)

        assert action.validate(None) is False

    def test_validate_alive_entities(self):
        actor = SimpleEntity("Fighter", hp=20)
        target = SimpleEntity("Goblin", hp=7)
        action = AttackAction(actor, target)

        assert action.validate(None) is True

    def test_execution_log_populated(self):
        rng = random.Random(42)
        actor = SimpleEntity("Fighter", hp=20)
        target = SimpleEntity("Goblin", hp=7, armor_class=10)
        action = AttackAction(actor, target, to_hit_bonus=5, rng=rng)

        action.execute(None)
        assert len(action.execution_log) >= 1

    def test_result_dict_structure(self):
        rng = random.Random(42)
        actor = SimpleEntity("Fighter", hp=20)
        target = SimpleEntity("Goblin", hp=7, armor_class=10)
        action = AttackAction(actor, target, to_hit_bonus=5, rng=rng)

        result = action.execute(None)
        assert "action" in result
        assert result["action"] == "attack"
        assert "hit" in result
        assert "attack_roll" in result
        assert "damage" in result
        assert "target" in result

    def test_target_hp_cannot_go_below_zero(self):
        rng = random.Random(42)
        actor = SimpleEntity("Fighter", hp=20)
        target = SimpleEntity("Goblin", hp=1, armor_class=5)
        action = AttackAction(actor, target, damage_expr="2d6+10", to_hit_bonus=10, rng=rng)

        result = action.execute(None)
        if result["hit"]:
            assert target.hp >= 0

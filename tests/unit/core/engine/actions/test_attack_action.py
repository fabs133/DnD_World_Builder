"""Tests for AttackAction."""

import random
import pytest
from core.engine.actions.attack_action import AttackAction


class SimpleEntity:
    def __init__(self, name, hp=10, armor_class=12, position=None):
        self.name = name
        self.hp = hp
        self.armor_class = armor_class
        self.position = position


class TestAttackAction:
    def test_hit_reduces_target_hp(self):
        # Seed 0 rolls 13 on d20; +5 = 18 vs AC 10 → guaranteed hit
        rng = random.Random(0)
        actor = SimpleEntity("Fighter", hp=20)
        target = SimpleEntity("Goblin", hp=7, armor_class=10)

        action = AttackAction(
            actor, target, damage_expr="1d6", to_hit_bonus=5, rng=rng
        )
        result = action.execute(None)

        assert result["hit"] is True
        assert target.hp < 7
        assert result["damage"] > 0

    def test_miss_does_not_reduce_hp(self):
        # Seed 2 rolls 2 on d20; +0 = 2 vs AC 30 → guaranteed miss
        rng = random.Random(2)
        actor = SimpleEntity("Fighter", hp=20)
        target = SimpleEntity("Dragon", hp=100, armor_class=30)

        action = AttackAction(
            actor, target, damage_expr="1d6", to_hit_bonus=0, rng=rng
        )
        result = action.execute(None)

        assert result["hit"] is False
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
        # Seed 0 rolls 13; +10 = 23 vs AC 5 → guaranteed hit
        rng = random.Random(0)
        actor = SimpleEntity("Fighter", hp=20)
        target = SimpleEntity("Goblin", hp=1, armor_class=5)
        action = AttackAction(actor, target, damage_expr="2d6+10", to_hit_bonus=10, rng=rng)

        result = action.execute(None)
        assert result["hit"] is True
        assert target.hp >= 0


class TestAttackRange:
    def test_validate_melee_in_range(self):
        """Melee attack (5ft) succeeds when target is adjacent."""
        actor = SimpleEntity("A", hp=10, position=(0, 0))
        target = SimpleEntity("B", hp=10, position=(0, 1))
        action = AttackAction(actor, target, weapon_range=5)
        assert action.validate(None) is True

    def test_validate_melee_out_of_range(self):
        """Melee attack fails when target is more than 1 tile away."""
        actor = SimpleEntity("A", hp=10, position=(0, 0))
        target = SimpleEntity("B", hp=10, position=(0, 5))
        action = AttackAction(actor, target, weapon_range=5)
        assert action.validate(None) is False
        assert "away" in action.execution_log[-1]

    def test_validate_ranged_in_range(self):
        """Ranged attack (30ft) succeeds at 6 tiles."""
        actor = SimpleEntity("A", hp=10, position=(0, 0))
        target = SimpleEntity("B", hp=10, position=(6, 0))
        action = AttackAction(actor, target, weapon_range=30)
        assert action.validate(None) is True

    def test_validate_ranged_out_of_range(self):
        """Ranged attack (30ft) fails at 7 tiles."""
        actor = SimpleEntity("A", hp=10, position=(0, 0))
        target = SimpleEntity("B", hp=10, position=(7, 0))
        action = AttackAction(actor, target, weapon_range=30)
        assert action.validate(None) is False

    def test_validate_no_positions_skips_range_check(self):
        """When positions are None, range check is skipped."""
        actor = SimpleEntity("A", hp=10)
        target = SimpleEntity("B", hp=10)
        action = AttackAction(actor, target, weapon_range=5)
        assert action.validate(None) is True

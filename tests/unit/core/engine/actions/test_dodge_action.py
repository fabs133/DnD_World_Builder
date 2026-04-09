"""Tests for DodgeAction and AttackAction disadvantage interaction."""

import random
import pytest
from core.engine.actions.dodge_action import DodgeAction
from core.engine.actions.attack_action import AttackAction


class SimpleEntity:
    def __init__(self, name, hp=10, armor_class=12, position=None):
        self.name = name
        self.hp = hp
        self.armor_class = armor_class
        self.position = position
        self.dodging = False
        self.has_advantage = False


class TestDodgeAction:
    def test_validate_alive(self):
        actor = SimpleEntity("Fighter")
        action = DodgeAction(actor)
        assert action.validate(None) is True

    def test_validate_dead(self):
        actor = SimpleEntity("Fighter", hp=0)
        action = DodgeAction(actor)
        assert action.validate(None) is False

    def test_execute_sets_dodging_flag(self):
        actor = SimpleEntity("Fighter")
        action = DodgeAction(actor)
        result = action.execute(None)
        assert actor.dodging is True
        assert result["action"] == "dodge"

    def test_execution_log_populated(self):
        actor = SimpleEntity("Fighter")
        action = DodgeAction(actor)
        action.execute(None)
        assert len(action.execution_log) > 0
        assert "Dodge" in action.execution_log[0]


class TestDodgeDisadvantage:
    def test_attack_against_dodging_uses_lower_roll(self):
        """When target is dodging, attacker rolls with disadvantage."""
        # Use a seeded RNG where we can predict behavior
        attacker = SimpleEntity("Goblin", hp=10)
        target = SimpleEntity("Fighter", hp=20, armor_class=10)
        target.dodging = True

        # Run many attacks and verify the mechanic works
        hits_with_dodge = 0
        hits_without_dodge = 0

        for seed in range(100):
            # With dodge (disadvantage)
            target_d = SimpleEntity("Fighter", hp=20, armor_class=15)
            target_d.dodging = True
            action_d = AttackAction(attacker, target_d, to_hit_bonus=5,
                                    rng=random.Random(seed))
            result_d = action_d.execute(None)
            if result_d["hit"]:
                hits_with_dodge += 1

            # Without dodge (normal)
            target_n = SimpleEntity("Fighter", hp=20, armor_class=15)
            target_n.dodging = False
            action_n = AttackAction(attacker, target_n, to_hit_bonus=5,
                                    rng=random.Random(seed))
            result_n = action_n.execute(None)
            if result_n["hit"]:
                hits_without_dodge += 1

        # Disadvantage should produce fewer hits on average
        assert hits_with_dodge < hits_without_dodge

    def test_dodge_noted_in_execution_log(self):
        attacker = SimpleEntity("Goblin", hp=10)
        target = SimpleEntity("Fighter", hp=20, armor_class=10)
        target.dodging = True

        action = AttackAction(attacker, target, to_hit_bonus=5,
                              rng=random.Random(42))
        action.execute(None)

        logs = " ".join(action.execution_log)
        assert "dodging" in logs.lower() or "disadvantage" in logs.lower() or "[dis]" in logs.lower()

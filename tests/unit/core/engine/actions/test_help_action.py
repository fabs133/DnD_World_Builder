"""Tests for HelpAction and AttackAction advantage interaction."""

import random
import pytest
from core.engine.actions.help_action import HelpAction
from core.engine.actions.attack_action import AttackAction


class SimpleEntity:
    def __init__(self, name, hp=10, armor_class=12):
        self.name = name
        self.hp = hp
        self.armor_class = armor_class
        self.helping = False
        self.has_advantage = False
        self.dodging = False


class TestHelpAction:
    def test_validate_alive(self):
        actor = SimpleEntity("Cleric")
        action = HelpAction(actor)
        assert action.validate(None) is True

    def test_validate_dead(self):
        actor = SimpleEntity("Cleric", hp=0)
        action = HelpAction(actor)
        assert action.validate(None) is False

    def test_execute_no_target(self):
        actor = SimpleEntity("Cleric")
        action = HelpAction(actor)
        result = action.execute(None)
        assert result["action"] == "help"
        assert "target" not in result

    def test_execute_with_target_grants_advantage(self):
        actor = SimpleEntity("Cleric")
        ally = SimpleEntity("Fighter")
        action = HelpAction(actor, target=ally)
        result = action.execute(None)
        assert ally.has_advantage is True
        assert result["target"] == "Fighter"

    def test_execution_log_with_target(self):
        actor = SimpleEntity("Cleric")
        ally = SimpleEntity("Fighter")
        action = HelpAction(actor, target=ally)
        action.execute(None)
        assert len(action.execution_log) > 0
        assert "Fighter" in action.execution_log[0]


class TestAdvantageOnAttack:
    def test_attack_with_advantage_uses_higher_roll(self):
        """When attacker has advantage, uses higher of two rolls."""
        hits_with_advantage = 0
        hits_without_advantage = 0

        for seed in range(100):
            # With advantage
            attacker_a = SimpleEntity("Fighter", hp=10)
            attacker_a.has_advantage = True
            target_a = SimpleEntity("Goblin", hp=10, armor_class=15)
            action_a = AttackAction(attacker_a, target_a, to_hit_bonus=3,
                                    rng=random.Random(seed))
            result_a = action_a.execute(None)
            if result_a["hit"]:
                hits_with_advantage += 1

            # Without advantage
            attacker_n = SimpleEntity("Fighter", hp=10)
            attacker_n.has_advantage = False
            target_n = SimpleEntity("Goblin", hp=10, armor_class=15)
            action_n = AttackAction(attacker_n, target_n, to_hit_bonus=3,
                                    rng=random.Random(seed))
            result_n = action_n.execute(None)
            if result_n["hit"]:
                hits_without_advantage += 1

        # Advantage should produce more hits on average
        assert hits_with_advantage > hits_without_advantage

    def test_advantage_noted_in_execution_log(self):
        attacker = SimpleEntity("Fighter", hp=10)
        attacker.has_advantage = True
        target = SimpleEntity("Goblin", hp=10, armor_class=10)

        action = AttackAction(attacker, target, to_hit_bonus=5,
                              rng=random.Random(42))
        action.execute(None)

        logs = " ".join(action.execution_log)
        assert "advantage" in logs.lower() or "[adv]" in logs.lower()

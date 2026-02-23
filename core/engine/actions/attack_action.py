"""Melee/ranged attack action with D&D 5e rules."""

from __future__ import annotations

import random
import re
from typing import Any

from models.flow.action.action import Action
from core.logger import app_logger


class AttackAction(Action):
    """A melee or ranged attack against a target entity.

    Args:
        actor: The attacking entity.
        target: The defending entity.
        weapon_range: Range in feet (5 for melee).
        damage_expr: Dice expression for damage (e.g., "1d6+2").
        to_hit_bonus: Attack roll modifier.
        rng: Optional Random instance for deterministic rolls.
    """

    def __init__(
        self,
        actor: Any,
        target: Any,
        weapon_range: int = 5,
        damage_expr: str = "1d6",
        to_hit_bonus: int = 0,
        rng: random.Random | None = None,
    ):
        super().__init__(actor)
        self.target = target
        self.weapon_range = weapon_range
        self.damage_expr = damage_expr
        self.to_hit_bonus = to_hit_bonus
        self._rng = rng or random.Random()

    def validate(self, game_state) -> bool:
        if getattr(self.actor, "hp", 0) <= 0:
            self.execution_log.append("Actor is dead")
            return False
        if getattr(self.target, "hp", 0) <= 0:
            self.execution_log.append("Target is already dead")
            return False
        return True

    def execute(self, game_state) -> dict:
        actor_name = self.actor.name
        target_name = self.target.name
        target_ac = getattr(self.target, "armor_class", 10)

        attack_roll = self._rng.randint(1, 20) + self.to_hit_bonus
        self.execution_log.append(
            f"{actor_name} rolls {attack_roll} vs AC {target_ac}"
        )

        if attack_roll >= target_ac:
            damage = self._roll_damage()
            old_hp = getattr(self.target, "hp", 0)
            self.target.hp = max(0, old_hp - damage)
            self.execution_log.append(
                f"{actor_name} hits {target_name} for {damage} damage "
                f"({old_hp} -> {self.target.hp} HP)"
            )
            app_logger.info(
                f"[Attack] {actor_name} hits {target_name}: "
                f"{damage} damage ({old_hp}->{self.target.hp})"
            )
            return {
                "action": "attack",
                "hit": True,
                "attack_roll": attack_roll,
                "damage": damage,
                "target": target_name,
                "target_hp": self.target.hp,
            }
        else:
            self.execution_log.append(f"{actor_name} misses {target_name}")
            app_logger.info(f"[Attack] {actor_name} misses {target_name}")
            return {
                "action": "attack",
                "hit": False,
                "attack_roll": attack_roll,
                "damage": 0,
                "target": target_name,
                "target_hp": getattr(self.target, "hp", 0),
            }

    def _roll_damage(self) -> int:
        """Roll damage dice using the instance's seeded RNG."""
        match = re.match(r"(\d*)d(\d+)([+-]?\d*)", self.damage_expr.replace(" ", ""))
        if not match:
            raise ValueError(f"Invalid dice expression: {self.damage_expr}")
        num_dice = int(match.group(1)) if match.group(1) else 1
        dice_sides = int(match.group(2))
        modifier = int(match.group(3)) if match.group(3) else 0
        rolls = [self._rng.randint(1, dice_sides) for _ in range(num_dice)]
        return sum(rolls) + modifier

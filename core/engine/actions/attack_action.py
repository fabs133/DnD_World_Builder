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

        # Range check (skipped when positions aren't set)
        actor_pos = getattr(self.actor, "position", None)
        target_pos = getattr(self.target, "position", None)
        if actor_pos is not None and target_pos is not None:
            dx = abs(actor_pos[0] - target_pos[0])
            dy = abs(actor_pos[1] - target_pos[1])
            distance_ft = max(dx, dy) * 5  # Chebyshev distance, 5ft per tile
            if distance_ft > self.weapon_range:
                self.execution_log.append(
                    f"Target is {distance_ft}ft away (range: {self.weapon_range}ft)"
                )
                return False

        return True

    def execute(self, game_state) -> dict:
        from core.engine.check_runner import run_attack_roll, DiceRollType

        actor_name = self.actor.name
        target_name = self.target.name

        # Determine advantage/disadvantage from entity flags + conditions
        roll_type = DiceRollType.NORMAL
        if getattr(self.target, "dodging", False):
            roll_type = DiceRollType.DISADVANTAGE
        elif getattr(self.actor, "has_advantage", False):
            roll_type = DiceRollType.ADVANTAGE

        # Apply condition-based modifiers (override flag-based if stronger)
        try:
            from core.engine.condition_effects import get_condition_modifiers
            attacker_mods = get_condition_modifiers(
                getattr(self.actor, "conditions", []))
            target_mods = get_condition_modifiers(
                getattr(self.target, "conditions", []))
            # Attacker conditions affect attack roll
            if attacker_mods.attack_roll_type == DiceRollType.DISADVANTAGE:
                roll_type = DiceRollType.DISADVANTAGE
            elif (attacker_mods.attack_roll_type == DiceRollType.ADVANTAGE
                  and roll_type == DiceRollType.NORMAL):
                roll_type = DiceRollType.ADVANTAGE
            # Target conditions grant advantage/disadvantage to attacker
            if target_mods.attacks_against_roll_type == DiceRollType.ADVANTAGE:
                if roll_type == DiceRollType.DISADVANTAGE:
                    roll_type = DiceRollType.NORMAL  # cancel
                else:
                    roll_type = DiceRollType.ADVANTAGE
            elif target_mods.attacks_against_roll_type == DiceRollType.DISADVANTAGE:
                if roll_type == DiceRollType.ADVANTAGE:
                    roll_type = DiceRollType.NORMAL  # cancel
                else:
                    roll_type = DiceRollType.DISADVANTAGE
        except ImportError:
            pass

        # Roll attack via unified check runner
        check = run_attack_roll(
            self.actor, self.target,
            to_hit_bonus=self.to_hit_bonus,
            roll_type=roll_type,
            rng=self._rng,
        )
        attack_roll = check.total
        natural = check.natural_roll
        target_ac = check.dc
        self.execution_log.append(check.message)

        if check.passed:
            damage, individual_dice = self._roll_damage_detailed()
            old_hp = getattr(self.target, "hp", 0)
            if hasattr(self.target, "take_damage"):
                self.target.take_damage(damage)
            else:
                self.target.hp = max(0, old_hp - damage)
            self.execution_log.append(
                f"{actor_name} hits {target_name} for {damage} damage "
                f"({old_hp} -> {self.target.hp} HP)"
            )
            app_logger.info(
                f"[Attack] {actor_name} hits {target_name}: "
                f"{damage} damage ({old_hp}->{self.target.hp})"
            )

            # Fire ON_DAMAGE event for trigger system
            world = getattr(self, "_world", None)
            if world:
                from core.gameCreation.event_bus import EventBus
                from core.events import TRIGGER_ON_DAMAGE
                EventBus.emit(TRIGGER_ON_DAMAGE, {
                    "entity": self.actor,
                    "target": self.target,
                    "damage": damage,
                    "damage_type": "weapon",
                    "position": getattr(self.target, "position", None),
                    "world": world,
                })

            self._emit_attack_resolved(
                True, attack_roll, natural, target_ac, damage, individual_dice)
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
            self._emit_attack_resolved(False, attack_roll, natural, target_ac)
            return {
                "action": "attack",
                "hit": False,
                "attack_roll": attack_roll,
                "damage": 0,
                "target": target_name,
                "target_hp": getattr(self.target, "hp", 0),
            }

    def _emit_attack_resolved(self, hit: bool, attack_roll: int,
                               natural: int, target_ac: int,
                               damage: int = 0, individual_dice: list | None = None):
        """Emit attack_resolved event for the encounter strip UI."""
        try:
            from core.gameCreation.event_bus import EventBus
            EventBus.emit("attack_resolved", {
                "attacker": self.actor,
                "defender": self.target,
                "attack_roll": attack_roll,
                "natural_roll": natural,
                "target_ac": target_ac,
                "hit": hit,
                "damage_expr": self.damage_expr,
                "damage_total": damage,
                "damage_type": "weapon",
                "is_critical": natural == 20,
                "individual_dice": individual_dice or [],
            })
        except Exception:
            pass

    def _roll_damage(self) -> int:
        """Roll damage dice using the instance's seeded RNG."""
        total, _ = self._roll_damage_detailed()
        return total

    def _roll_damage_detailed(self) -> tuple[int, list[int]]:
        """Roll damage dice, returning (total, individual_rolls)."""
        match = re.match(r"(\d*)d(\d+)([+-]?\d*)", self.damage_expr.replace(" ", ""))
        if not match:
            raise ValueError(f"Invalid dice expression: {self.damage_expr}")
        num_dice = int(match.group(1)) if match.group(1) else 1
        dice_sides = int(match.group(2))
        modifier = int(match.group(3)) if match.group(3) else 0
        rolls = [self._rng.randint(1, dice_sides) for _ in range(num_dice)]
        return sum(rolls) + modifier, rolls

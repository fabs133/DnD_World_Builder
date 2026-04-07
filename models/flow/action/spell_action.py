"""Spell casting action — validate slots, apply effects, emit events."""

from __future__ import annotations

import random
import re
from typing import Any

from core.events import (
    CONDITION_APPLIED, ENTITY_DAMAGED, ENTITY_DIED, ENTITY_HEALED,
    SPELL_CAST,
)
from core.logger import app_logger
from models.flow.action.action import Action, roll, apply_effect


class SpellAction(Action):
    """Cast a spell on one or more targets.

    Follows the same validate/execute pattern as AttackAction:
    - validate() returns bool, appends to execution_log on failure
    - execute() applies effects, emits EventBus events, returns result dict
    """

    def __init__(self, caster, spell, targets, rng: random.Random | None = None):
        super().__init__(caster)
        self.spell = spell
        self.targets = targets if isinstance(targets, list) else [targets]
        self._rng = rng or random.Random()

    def validate(self, game_state) -> bool:
        if getattr(self.actor, "hp", 0) <= 0:
            self.execution_log.append("Caster is dead")
            return False

        # Check caster knows this spell
        known = getattr(self.actor, "spells", [])
        spell_names = []
        for s in known:
            if hasattr(s, "name"):
                spell_names.append(s.name)
            elif isinstance(s, dict):
                spell_names.append(s.get("name", ""))
            else:
                spell_names.append(str(s))

        spell_name = self.spell.name if hasattr(self.spell, "name") else str(self.spell)
        if spell_name not in spell_names:
            self.execution_log.append(f"{self.actor.name} does not know {spell_name}")
            return False

        # Check spell slot availability (cantrips = level 0, free)
        level = getattr(self.spell, "level", 0)
        if level > 0:
            slots = getattr(self.actor, "spell_slots", 0)
            if isinstance(slots, int):
                if slots <= 0:
                    self.execution_log.append("No spell slots remaining")
                    return False
            elif isinstance(slots, dict):
                has_slot = False
                for lvl in range(level, 10):
                    slot_info = slots.get(lvl, 0)
                    remaining = slot_info
                    if isinstance(slot_info, dict):
                        remaining = slot_info.get("maximum", 0) - slot_info.get("used", 0)
                    if remaining > 0:
                        has_slot = True
                        break
                if not has_slot:
                    self.execution_log.append(
                        f"No spell slots of level {level} or higher")
                    return False

        # Check targets exist (non-self spells)
        spell_range = getattr(self.spell, "range", None)
        if spell_range and str(spell_range).lower() != "self":
            if not self.targets:
                self.execution_log.append("No target selected")
                return False
            # Check at least one target is alive
            alive = [t for t in self.targets if getattr(t, "hp", 1) > 0]
            if not alive:
                self.execution_log.append("All targets are dead")
                return False

        return True

    def execute(self, game_state) -> dict:
        caster_name = getattr(self.actor, "name", "?")
        spell_name = self.spell.name if hasattr(self.spell, "name") else str(self.spell)
        level = getattr(self.spell, "level", 0)

        # Deduct spell slot
        if level > 0:
            self._deduct_spell_slot()

        self.execution_log.append(
            f"{caster_name} casts {spell_name} (level {level})")

        results = []
        for target in self.targets:
            target_name = getattr(target, "name", "?")
            target_result = {"target": target_name}

            # Damage
            if self.spell.damage:
                damage_expr = self.spell.damage.get("amount", "1d6")
                damage_type = self.spell.damage.get("type", "magical")
                damage = self._roll_dice(damage_expr)
                old_hp = getattr(target, "hp", 0)
                target.hp = max(0, old_hp - damage)
                target_result["damage"] = damage
                target_result["damage_type"] = damage_type
                self.execution_log.append(
                    f"  {target_name} takes {damage} {damage_type} damage "
                    f"({old_hp} -> {target.hp} HP)")

                self._emit(ENTITY_DAMAGED, {
                    "entity_name": target_name,
                    "source": caster_name,
                    "damage": damage,
                    "damage_type": damage_type,
                    "position": getattr(target, "position", None),
                })

                if target.hp <= 0:
                    self.execution_log.append(f"  {target_name} is defeated!")
                    self._emit(ENTITY_DIED, {
                        "entity_name": target_name,
                        "source": caster_name,
                        "position": getattr(target, "position", None),
                    })

            # Healing
            if self.spell.healing:
                heal_expr = self.spell.healing.get("amount", "1d8")
                heal_amount = self._roll_dice(heal_expr)
                old_hp = getattr(target, "hp", 0)
                max_hp = getattr(target, "max_hp", old_hp)
                target.hp = min(max_hp, old_hp + heal_amount)
                actual = target.hp - old_hp
                target_result["healed"] = actual
                self.execution_log.append(
                    f"  {target_name} healed for {actual} HP "
                    f"({old_hp} -> {target.hp})")

                self._emit(ENTITY_HEALED, {
                    "entity_name": target_name,
                    "source": caster_name,
                    "amount": actual,
                    "position": getattr(target, "position", None),
                })

            # Status effect
            if self.spell.effect:
                apply_effect(target, self.spell.effect)
                effect_type = self.spell.effect.get("type", "unknown")
                self.execution_log.append(
                    f"  {target_name} gains effect: {effect_type}")
                self._emit(CONDITION_APPLIED, {
                    "entity_name": target_name,
                    "condition": effect_type,
                    "source": caster_name,
                    "position": getattr(target, "position", None),
                })

            results.append(target_result)

        # Spell cast event (CombatAnimator listens for this)
        self._emit(SPELL_CAST, {
            "caster": caster_name,
            "spell": spell_name,
            "level": level,
            "targets": [getattr(t, "name", "?") for t in self.targets],
            "position": getattr(self.actor, "position", None),
        })

        app_logger.info(f"[Spell] {caster_name} casts {spell_name}")

        return {
            "action": "spell",
            "spell": spell_name,
            "level": level,
            "caster": caster_name,
            "results": results,
        }

    def _deduct_spell_slot(self) -> None:
        level = getattr(self.spell, "level", 0)
        slots = getattr(self.actor, "spell_slots", None)
        if slots is None:
            return

        # Store max for long rest recovery
        if not hasattr(self.actor, "_max_spell_slots"):
            if isinstance(slots, int):
                self.actor._max_spell_slots = slots
            elif isinstance(slots, dict):
                import copy
                self.actor._max_spell_slots = copy.deepcopy(slots)

        if isinstance(slots, int):
            self.actor.spell_slots = max(0, slots - 1)
        elif isinstance(slots, dict):
            for lvl in range(level, 10):
                slot_info = slots.get(lvl, 0)
                if isinstance(slot_info, dict):
                    remaining = slot_info.get("maximum", 0) - slot_info.get("used", 0)
                    if remaining > 0:
                        slot_info["used"] = slot_info.get("used", 0) + 1
                        break
                elif isinstance(slot_info, int) and slot_info > 0:
                    slots[lvl] = slot_info - 1
                    break

    def _roll_dice(self, expression: str) -> int:
        match = re.match(r"(\d*)d(\d+)([+-]?\d*)", expression.replace(" ", ""))
        if not match:
            return 0
        num = int(match.group(1)) if match.group(1) else 1
        sides = int(match.group(2))
        mod = int(match.group(3)) if match.group(3) else 0
        return sum(self._rng.randint(1, sides) for _ in range(num)) + mod

    def _emit(self, event_name: str, data: dict) -> None:
        try:
            from core.gameCreation.event_bus import EventBus
            EventBus.emit(event_name, data)
        except Exception:
            pass

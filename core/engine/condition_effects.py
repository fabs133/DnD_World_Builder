"""Condition effects — maps D&D 5e conditions to mechanical modifiers.

Used by combat actions and the check runner to apply advantage/disadvantage,
movement restrictions, and auto-fail rules based on active conditions.
"""

from __future__ import annotations

from dataclasses import dataclass
from domain.specs.checks import DiceRollType


@dataclass(frozen=True)
class ConditionModifiers:
    """Mechanical effects of active conditions on an entity."""

    attack_roll_type: DiceRollType = DiceRollType.NORMAL
    ability_check_roll_type: DiceRollType = DiceRollType.NORMAL
    dex_save_roll_type: DiceRollType = DiceRollType.NORMAL
    str_save_roll_type: DiceRollType = DiceRollType.NORMAL
    attacks_against_roll_type: DiceRollType = DiceRollType.NORMAL
    speed_multiplier: float = 1.0
    can_take_actions: bool = True
    can_move: bool = True
    auto_fail_str_dex_saves: bool = False
    auto_crit_melee_against: bool = False


# ── Per-condition effect definitions ─────────────────────────────

_CONDITION_EFFECTS: dict[str, dict] = {
    "blinded": {
        "attack_roll_type": DiceRollType.DISADVANTAGE,
        "attacks_against_roll_type": DiceRollType.ADVANTAGE,
    },
    "charmed": {
        # Can't attack the charmer — enforced at action level, not here
    },
    "deafened": {
        # No mechanical combat effect
    },
    "frightened": {
        "attack_roll_type": DiceRollType.DISADVANTAGE,
        "ability_check_roll_type": DiceRollType.DISADVANTAGE,
    },
    "grappled": {
        "speed_multiplier": 0.0,
    },
    "incapacitated": {
        "can_take_actions": False,
    },
    "invisible": {
        "attack_roll_type": DiceRollType.ADVANTAGE,
        "attacks_against_roll_type": DiceRollType.DISADVANTAGE,
    },
    "paralyzed": {
        "can_take_actions": False,
        "can_move": False,
        "auto_fail_str_dex_saves": True,
        "attacks_against_roll_type": DiceRollType.ADVANTAGE,
        "auto_crit_melee_against": True,
    },
    "petrified": {
        "can_take_actions": False,
        "can_move": False,
        "auto_fail_str_dex_saves": True,
        "attacks_against_roll_type": DiceRollType.ADVANTAGE,
    },
    "poisoned": {
        "attack_roll_type": DiceRollType.DISADVANTAGE,
        "ability_check_roll_type": DiceRollType.DISADVANTAGE,
    },
    "prone": {
        "attack_roll_type": DiceRollType.DISADVANTAGE,
        # Melee attacks against have advantage, ranged have disadvantage
        # — handled specially in get_attack_modifiers()
    },
    "restrained": {
        "speed_multiplier": 0.0,
        "attack_roll_type": DiceRollType.DISADVANTAGE,
        "dex_save_roll_type": DiceRollType.DISADVANTAGE,
        "attacks_against_roll_type": DiceRollType.ADVANTAGE,
    },
    "stunned": {
        "can_take_actions": False,
        "auto_fail_str_dex_saves": True,
        "attacks_against_roll_type": DiceRollType.ADVANTAGE,
    },
    "unconscious": {
        "can_take_actions": False,
        "can_move": False,
        "auto_fail_str_dex_saves": True,
        "attacks_against_roll_type": DiceRollType.ADVANTAGE,
        "auto_crit_melee_against": True,
    },
    "exhausted": {
        "ability_check_roll_type": DiceRollType.DISADVANTAGE,
        # Further exhaustion levels (speed halved, etc.) not modeled
    },
    "inspired": {
        # Positive condition from side events — advantage on next check
        "ability_check_roll_type": DiceRollType.ADVANTAGE,
    },
}


def get_condition_modifiers(conditions: list[str]) -> ConditionModifiers:
    """Combine all active condition effects into a single modifiers object.

    When multiple conditions conflict (one gives advantage, another
    disadvantage), they cancel out to NORMAL per D&D 5e rules.
    """
    # Track advantage/disadvantage counts per category
    adv = {"atk": 0, "dis_atk": 0, "check": 0, "dis_check": 0,
           "dex_save": 0, "dis_dex": 0, "str_save": 0, "dis_str": 0,
           "against": 0, "dis_against": 0}
    speed_mult = 1.0
    can_act = True
    can_move = True
    auto_fail = False
    auto_crit = False

    for cond in conditions:
        effects = _CONDITION_EFFECTS.get(cond.lower(), {})
        if not effects:
            continue

        # Attack roll
        rt = effects.get("attack_roll_type")
        if rt == DiceRollType.ADVANTAGE:
            adv["atk"] += 1
        elif rt == DiceRollType.DISADVANTAGE:
            adv["dis_atk"] += 1

        # Ability checks
        rt = effects.get("ability_check_roll_type")
        if rt == DiceRollType.ADVANTAGE:
            adv["check"] += 1
        elif rt == DiceRollType.DISADVANTAGE:
            adv["dis_check"] += 1

        # DEX saves
        rt = effects.get("dex_save_roll_type")
        if rt == DiceRollType.DISADVANTAGE:
            adv["dis_dex"] += 1

        # STR saves
        rt = effects.get("str_save_roll_type")
        if rt == DiceRollType.DISADVANTAGE:
            adv["dis_str"] += 1

        # Attacks against this entity
        rt = effects.get("attacks_against_roll_type")
        if rt == DiceRollType.ADVANTAGE:
            adv["against"] += 1
        elif rt == DiceRollType.DISADVANTAGE:
            adv["dis_against"] += 1

        # Speed
        sm = effects.get("speed_multiplier")
        if sm is not None:
            speed_mult = min(speed_mult, sm)

        # Action restrictions
        if effects.get("can_take_actions") is False:
            can_act = False
        if effects.get("can_move") is False:
            can_move = False
        if effects.get("auto_fail_str_dex_saves"):
            auto_fail = True
        if effects.get("auto_crit_melee_against"):
            auto_crit = True

    def _resolve(adv_count, dis_count):
        if adv_count > 0 and dis_count > 0:
            return DiceRollType.NORMAL  # cancel out
        if adv_count > 0:
            return DiceRollType.ADVANTAGE
        if dis_count > 0:
            return DiceRollType.DISADVANTAGE
        return DiceRollType.NORMAL

    return ConditionModifiers(
        attack_roll_type=_resolve(adv["atk"], adv["dis_atk"]),
        ability_check_roll_type=_resolve(adv["check"], adv["dis_check"]),
        dex_save_roll_type=_resolve(adv["dex_save"], adv["dis_dex"]),
        str_save_roll_type=_resolve(adv["str_save"], adv["dis_str"]),
        attacks_against_roll_type=_resolve(adv["against"], adv["dis_against"]),
        speed_multiplier=speed_mult,
        can_take_actions=can_act,
        can_move=can_move,
        auto_fail_str_dex_saves=auto_fail,
        auto_crit_melee_against=auto_crit,
    )

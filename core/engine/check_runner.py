"""Unified dice rolling and skill/save check resolution.

Central module for ALL d20 checks in the game — combat attacks, exploration
skill checks, side event rolls, and saving throws. Wraps the pure
:mod:`domain.specs.checks` specifications with actual dice rolling and
entity stat extraction.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Optional

from domain.specs.checks import (
    DiceRollType, RollContext, SkillCheckSpec, SavingThrowSpec, SpecResult,
)

# ── Ability score mapping ────────────────────────────────────────

SKILL_TO_ABILITY: dict[str, str] = {
    "Acrobatics": "Dexterity",
    "Animal Handling": "Wisdom",
    "Arcana": "Intelligence",
    "Athletics": "Strength",
    "Deception": "Charisma",
    "History": "Intelligence",
    "Insight": "Wisdom",
    "Intimidation": "Charisma",
    "Investigation": "Intelligence",
    "Medicine": "Wisdom",
    "Nature": "Wisdom",
    "Perception": "Wisdom",
    "Performance": "Charisma",
    "Persuasion": "Charisma",
    "Religion": "Intelligence",
    "Sleight of Hand": "Dexterity",
    "Stealth": "Dexterity",
    "Survival": "Wisdom",
}


@dataclass(frozen=True)
class CheckResult:
    """Result of a d20 check — carries everything UI needs to display."""

    passed: bool
    total: int
    natural_roll: int
    modifier: int
    dc: int
    skill: str
    ability: str
    roll_type: DiceRollType
    message: str           # Human-readable: "Perception: d20(14) + WIS(+2) = 16 vs DC 12 — Success!"
    margin: int            # positive = passed by N, negative = failed by N
    rolls: tuple[int, ...]  # all individual die rolls (for display)


def _get_modifier(entity, skill: str) -> tuple[int, str]:
    """Extract the modifier for a skill from an entity.

    Returns (modifier, ability_name).
    """
    # First try direct skill modifier
    if hasattr(entity, "skill_modifiers"):
        mods = entity.skill_modifiers
        if isinstance(mods, dict) and skill in mods:
            ability = SKILL_TO_ABILITY.get(skill, skill)
            return int(mods[skill]), ability

    # Fall back to ability score → modifier
    ability = SKILL_TO_ABILITY.get(skill, skill)
    stats = getattr(entity, "stats", {})
    if isinstance(stats, dict):
        score = stats.get(ability, 10)
        try:
            return (int(score) - 10) // 2, ability
        except (ValueError, TypeError):
            pass
    return 0, ability


def _roll_d20(roll_type: DiceRollType = DiceRollType.NORMAL,
              rng: random.Random | None = None) -> tuple[int, int, tuple[int, ...]]:
    """Roll a d20 with advantage/disadvantage.

    Returns (final_roll, natural_roll, all_rolls).
    """
    r = rng or random
    roll1 = r.randint(1, 20)
    if roll_type == DiceRollType.ADVANTAGE:
        roll2 = r.randint(1, 20)
        natural = max(roll1, roll2)
        return natural, natural, (roll1, roll2)
    elif roll_type == DiceRollType.DISADVANTAGE:
        roll2 = r.randint(1, 20)
        natural = min(roll1, roll2)
        return natural, natural, (roll1, roll2)
    return roll1, roll1, (roll1,)


# ── Public API ───────────────────────────────────────────────────

def run_skill_check(
    entity,
    skill: str,
    dc: int,
    roll_type: DiceRollType = DiceRollType.NORMAL,
    rng: random.Random | None = None,
) -> CheckResult:
    """Roll a skill check for *entity* against *dc*.

    Automatically applies condition-based advantage/disadvantage.
    """
    # Apply condition modifiers to roll type
    try:
        from core.engine.condition_effects import get_condition_modifiers
        mods = get_condition_modifiers(getattr(entity, "conditions", []))
        if mods.ability_check_roll_type != DiceRollType.NORMAL:
            if roll_type == DiceRollType.NORMAL:
                roll_type = mods.ability_check_roll_type
            elif roll_type != mods.ability_check_roll_type:
                roll_type = DiceRollType.NORMAL  # cancel
    except ImportError:
        pass

    mod, ability = _get_modifier(entity, skill)
    final, natural, rolls = _roll_d20(roll_type, rng)
    total = final + mod
    passed = total >= dc
    margin = total - dc

    # Build the display message
    prefix = ""
    if roll_type == DiceRollType.ADVANTAGE:
        prefix = "[ADV] "
    elif roll_type == DiceRollType.DISADVANTAGE:
        prefix = "[DIS] "

    msg = (
        f"{prefix}{skill}: d20({final}) + {ability[:3].upper()}({mod:+d})"
        f" = {total} vs DC {dc}"
    )
    if passed:
        msg += f" — Success! (by {margin})"
    else:
        msg += f" — Failed. (by {abs(margin)})"

    return CheckResult(
        passed=passed,
        total=total,
        natural_roll=natural,
        modifier=mod,
        dc=dc,
        skill=skill,
        ability=ability,
        roll_type=roll_type,
        message=msg,
        margin=margin,
        rolls=rolls,
    )


def run_saving_throw(
    entity,
    ability: str,
    dc: int,
    roll_type: DiceRollType = DiceRollType.NORMAL,
    rng: random.Random | None = None,
) -> CheckResult:
    """Roll a saving throw for *entity* against *dc*."""
    stats = getattr(entity, "stats", {})
    score = stats.get(ability, 10) if isinstance(stats, dict) else 10
    try:
        mod = (int(score) - 10) // 2
    except (ValueError, TypeError):
        mod = 0

    # Check for save proficiency
    if hasattr(entity, "save_modifiers"):
        sm = entity.save_modifiers
        if isinstance(sm, dict) and ability in sm:
            mod = int(sm[ability])

    final, natural, rolls = _roll_d20(roll_type, rng)
    total = final + mod
    passed = total >= dc
    margin = total - dc

    prefix = ""
    if roll_type == DiceRollType.ADVANTAGE:
        prefix = "[ADV] "
    elif roll_type == DiceRollType.DISADVANTAGE:
        prefix = "[DIS] "

    msg = (
        f"{prefix}{ability} save: d20({final}) + {ability[:3].upper()}({mod:+d})"
        f" = {total} vs DC {dc}"
    )
    if passed:
        msg += f" — Success! (by {margin})"
    else:
        msg += f" — Failed. (by {abs(margin)})"

    return CheckResult(
        passed=passed,
        total=total,
        natural_roll=natural,
        modifier=mod,
        dc=dc,
        skill=f"{ability} save",
        ability=ability,
        roll_type=roll_type,
        message=msg,
        margin=margin,
        rolls=rolls,
    )


def run_attack_roll(
    attacker,
    target,
    to_hit_bonus: int = 0,
    roll_type: DiceRollType = DiceRollType.NORMAL,
    rng: random.Random | None = None,
) -> CheckResult:
    """Roll an attack against *target*'s AC.

    The *to_hit_bonus* is the attacker's attack modifier (proficiency +
    ability mod, pre-computed by the caller).
    """
    target_ac = getattr(target, "armor_class", 10)
    if hasattr(target, "stats") and isinstance(target.stats, dict):
        target_ac = target.stats.get("armor_class", target_ac)

    final, natural, rolls = _roll_d20(roll_type, rng)
    total = final + to_hit_bonus
    is_crit = (natural == 20)
    is_fumble = (natural == 1)

    if is_fumble:
        passed = False
    elif is_crit:
        passed = True
    else:
        passed = total >= target_ac

    margin = total - target_ac

    prefix = ""
    if roll_type == DiceRollType.ADVANTAGE:
        prefix = "[ADV] "
    elif roll_type == DiceRollType.DISADVANTAGE:
        prefix = "[DIS] "

    crit_tag = ""
    if is_crit:
        crit_tag = " (Critical Hit!)"
    elif is_fumble:
        crit_tag = " (Fumble!)"

    msg = (
        f"{prefix}Attack: d20({final}) + ATK({to_hit_bonus:+d})"
        f" = {total} vs AC {target_ac}"
    )
    if passed:
        msg += f" — Hit!{crit_tag}"
    else:
        msg += f" — Miss.{crit_tag}"

    return CheckResult(
        passed=passed,
        total=total,
        natural_roll=natural,
        modifier=to_hit_bonus,
        dc=target_ac,
        skill="attack",
        ability="",
        roll_type=roll_type,
        message=msg,
        margin=margin,
        rolls=rolls,
    )

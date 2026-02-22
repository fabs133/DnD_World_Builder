"""
D&D 5e Skill Check Specifications

This module implements skill checks, saving throws, and ability checks
as composable specifications with full traceability.

Key features:
- Rich feedback: "Perception check: 8+3=11 vs DC 15 (failed by 4)"
- Advantage/disadvantage support
- Auto-pass/fail for critical rolls
- Deterministic evaluation (rolls provided via context, not generated)

Design note:
    Specs are PURE - they don't roll dice. The roll value comes from context.
    This enables:
    - Deterministic testing with fixed rolls
    - Replay of scenarios
    - "What if" analysis with different rolls
    
    The actual dice rolling happens in the application layer or UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from enum import Enum

from domain.specs.base import Specification, SpecResult


class DiceRollType(Enum):
    """Type of dice roll for the check."""
    NORMAL = "normal"
    ADVANTAGE = "advantage"
    DISADVANTAGE = "disadvantage"


@dataclass(frozen=True)
class RollContext:
    """
    Context for a dice-based check.
    
    This is what the application layer provides after rolling dice.
    
    Attributes:
        roll: The d20 roll result (after advantage/disadvantage)
        natural_roll: The unmodified die result (for crit detection)
        roll_type: Whether advantage/disadvantage was applied
        rolls: All individual die results (for display)
    """
    roll: int
    natural_roll: int = 0
    roll_type: DiceRollType = DiceRollType.NORMAL
    rolls: tuple[int, ...] = ()
    
    def __post_init__(self):
        # If natural_roll not provided, use roll
        if self.natural_roll == 0:
            object.__setattr__(self, "natural_roll", self.roll)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RollContext:
        return cls(
            roll=data["roll"],
            natural_roll=data.get("natural_roll", data["roll"]),
            roll_type=DiceRollType(data.get("roll_type", "normal")),
            rolls=tuple(data.get("rolls", [])),
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "roll": self.roll,
            "natural_roll": self.natural_roll,
            "roll_type": self.roll_type.value,
            "rolls": list(self.rolls),
        }


class SkillCheckSpec(Specification):
    """
    D&D 5e skill check specification.
    
    Evaluates whether an entity passes a skill check against a DC.
    The roll is provided via context, making this spec pure and testable.
    
    Args:
        skill: The skill name (e.g., "Perception", "Stealth", "Athletics")
        dc: Difficulty Class to meet or exceed
        auto_pass_on_nat_20: If True, natural 20 always passes
        auto_fail_on_nat_1: If True, natural 1 always fails
    
    Context requirements:
        - roll_context: RollContext with the dice roll
        OR
        - roll: int (simple roll value)
    
    Candidate requirements:
        - skill_modifiers: dict[str, int] mapping skill names to modifiers
        OR
        - stats: dict with skill modifiers
    
    Example:
        spec = SkillCheckSpec("Perception", dc=15)
        
        # Entity with +5 Perception, rolled 12
        result = spec.is_satisfied_by(
            entity,
            context={"roll_context": RollContext(roll=12)}
        )
        # result.passed = True (12 + 5 = 17 >= 15)
        # result.message = "Perception check: 12+5=17 vs DC 15"
    """
    
    def __init__(
        self,
        skill: str,
        dc: int,
        auto_pass_on_nat_20: bool = False,  # RAW: ability checks don't auto-pass
        auto_fail_on_nat_1: bool = False,   # RAW: ability checks don't auto-fail
    ):
        self.skill = skill
        self.dc = dc
        self.auto_pass_on_nat_20 = auto_pass_on_nat_20
        self.auto_fail_on_nat_1 = auto_fail_on_nat_1
    
    @property
    def rule_id(self) -> str:
        return f"skill_check_{self.skill.lower()}_dc{self.dc}"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        context = context or {}
        
        # Extract roll from context
        roll_ctx = self._get_roll_context(context)
        if roll_ctx is None:
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message=f"{self.skill} check requires a roll",
                suggested_fix="Provide 'roll' or 'roll_context' in context",
                tags=frozenset({"skill_check", "missing_roll", self.skill.lower()}),
                data={"error": "no_roll_provided"}
            )
        
        # Extract modifier from candidate
        modifier = self._get_modifier(candidate)
        
        # Check for auto-pass/fail on natural rolls
        if self.auto_pass_on_nat_20 and roll_ctx.natural_roll == 20:
            return self._make_result(
                passed=True,
                roll=roll_ctx.roll,
                modifier=modifier,
                total=roll_ctx.roll + modifier,
                natural_roll=roll_ctx.natural_roll,
                reason="Natural 20!"
            )
        
        if self.auto_fail_on_nat_1 and roll_ctx.natural_roll == 1:
            return self._make_result(
                passed=False,
                roll=roll_ctx.roll,
                modifier=modifier,
                total=roll_ctx.roll + modifier,
                natural_roll=roll_ctx.natural_roll,
                reason="Natural 1!"
            )
        
        # Normal check
        total = roll_ctx.roll + modifier
        passed = total >= self.dc
        
        return self._make_result(
            passed=passed,
            roll=roll_ctx.roll,
            modifier=modifier,
            total=total,
            natural_roll=roll_ctx.natural_roll,
            roll_type=roll_ctx.roll_type,
        )
    
    def _get_roll_context(self, context: dict[str, Any]) -> RollContext | None:
        """Extract RollContext from context dict."""
        if "roll_context" in context:
            rc = context["roll_context"]
            if isinstance(rc, RollContext):
                return rc
            return RollContext.from_dict(rc)
        
        if "roll" in context:
            return RollContext(roll=context["roll"])
        
        return None
    
    def _get_modifier(self, candidate: Any) -> int:
        """Extract skill modifier from candidate entity."""
        # Try different attribute patterns
        if hasattr(candidate, "skill_modifiers"):
            return candidate.skill_modifiers.get(self.skill, 0)
        
        if hasattr(candidate, "stats"):
            stats = candidate.stats
            if isinstance(stats, dict):
                return stats.get(self.skill, 0)
        
        if isinstance(candidate, dict):
            return candidate.get("skill_modifiers", {}).get(self.skill, 0)
        
        return 0
    
    def _make_result(
        self,
        passed: bool,
        roll: int,
        modifier: int,
        total: int,
        natural_roll: int,
        roll_type: DiceRollType = DiceRollType.NORMAL,
        reason: str | None = None,
    ) -> SpecResult:
        """Build a detailed SpecResult for the check."""
        margin = total - self.dc
        margin_str = f"by {abs(margin)}" if margin != 0 else "exactly"
        
        if reason:
            message = f"{self.skill} check: {reason}"
        else:
            sign = "+" if modifier >= 0 else ""
            result_word = "passed" if passed else "failed"
            message = f"{self.skill} check: {roll}{sign}{modifier}={total} vs DC {self.dc} ({result_word} {margin_str})"
        
        # Roll type indicator
        if roll_type == DiceRollType.ADVANTAGE:
            message = f"[ADV] {message}"
        elif roll_type == DiceRollType.DISADVANTAGE:
            message = f"[DIS] {message}"
        
        suggested_fix = None
        if not passed:
            needed = self.dc - modifier
            if needed <= 20:
                suggested_fix = f"Roll {needed}+ on d20 to pass"
            else:
                suggested_fix = f"DC {self.dc} impossible with modifier {modifier}"
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=passed,
            message=message,
            suggested_fix=suggested_fix,
            tags=frozenset({"skill_check", self.skill.lower(), "dice"}),
            data={
                "skill": self.skill,
                "dc": self.dc,
                "roll": roll,
                "natural_roll": natural_roll,
                "modifier": modifier,
                "total": total,
                "margin": margin,
                "roll_type": roll_type.value,
            }
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "SkillCheckSpec",
            "skill": self.skill,
            "dc": self.dc,
            "auto_pass_on_nat_20": self.auto_pass_on_nat_20,
            "auto_fail_on_nat_1": self.auto_fail_on_nat_1,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillCheckSpec:
        return cls(
            skill=data["skill"],
            dc=data["dc"],
            auto_pass_on_nat_20=data.get("auto_pass_on_nat_20", False),
            auto_fail_on_nat_1=data.get("auto_fail_on_nat_1", False),
        )


class SavingThrowSpec(Specification):
    """
    D&D 5e saving throw specification.
    
    Similar to SkillCheckSpec but for saving throws, with:
    - Different modifier lookup (ability saves, not skills)
    - Different auto-pass/fail defaults (death saves have special rules)
    
    Args:
        ability: The ability score ("STR", "DEX", "CON", "INT", "WIS", "CHA")
        dc: Difficulty Class
        is_death_save: Special handling for death saving throws
    """
    
    ABILITIES = {"STR", "DEX", "CON", "INT", "WIS", "CHA"}
    
    def __init__(
        self,
        ability: str,
        dc: int,
        is_death_save: bool = False,
    ):
        ability = ability.upper()
        if ability not in self.ABILITIES:
            raise ValueError(f"Invalid ability: {ability}. Must be one of {self.ABILITIES}")
        
        self.ability = ability
        self.dc = dc
        self.is_death_save = is_death_save
    
    @property
    def rule_id(self) -> str:
        prefix = "death_save" if self.is_death_save else f"save_{self.ability.lower()}"
        return f"{prefix}_dc{self.dc}"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        context = context or {}
        
        # Extract roll
        roll = context.get("roll")
        if roll is None:
            roll_ctx = context.get("roll_context")
            if roll_ctx:
                roll = roll_ctx.roll if isinstance(roll_ctx, RollContext) else roll_ctx.get("roll")
        
        if roll is None:
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message=f"{self.ability} save requires a roll",
                suggested_fix="Provide 'roll' in context",
                tags=frozenset({"saving_throw", "missing_roll"}),
            )
        
        # Natural roll for crit detection
        natural_roll = context.get("natural_roll", roll)
        
        # Get save modifier
        modifier = self._get_save_modifier(candidate)
        
        # Death save special rules
        if self.is_death_save:
            if natural_roll == 20:
                return SpecResult(
                    rule_id=self.rule_id,
                    passed=True,
                    message="Death save: Natural 20! Regain 1 HP",
                    tags=frozenset({"saving_throw", "death_save", "critical"}),
                    data={"natural_20": True, "regain_hp": 1}
                )
            if natural_roll == 1:
                return SpecResult(
                    rule_id=self.rule_id,
                    passed=False,
                    message="Death save: Natural 1! Two failures",
                    suggested_fix="Ally can stabilize with Medicine check or healing",
                    tags=frozenset({"saving_throw", "death_save", "critical"}),
                    data={"natural_1": True, "failures": 2}
                )
        
        # Normal save
        total = roll + modifier
        passed = total >= self.dc
        
        sign = "+" if modifier >= 0 else ""
        result_word = "passed" if passed else "failed"
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=passed,
            message=f"{self.ability} save: {roll}{sign}{modifier}={total} vs DC {self.dc} ({result_word})",
            suggested_fix=None if passed else f"Roll {self.dc - modifier}+ on d20",
            tags=frozenset({"saving_throw", self.ability.lower()}),
            data={
                "ability": self.ability,
                "dc": self.dc,
                "roll": roll,
                "modifier": modifier,
                "total": total,
                "margin": total - self.dc,
            }
        )
    
    def _get_save_modifier(self, candidate: Any) -> int:
        """Extract saving throw modifier from candidate."""
        if hasattr(candidate, "save_modifiers"):
            return candidate.save_modifiers.get(self.ability, 0)
        
        if hasattr(candidate, "stats"):
            stats = candidate.stats
            if isinstance(stats, dict):
                # Try save-specific first, then raw ability
                return stats.get(f"{self.ability}_save", stats.get(self.ability, 0))
        
        return 0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "SavingThrowSpec",
            "ability": self.ability,
            "dc": self.dc,
            "is_death_save": self.is_death_save,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SavingThrowSpec:
        return cls(
            ability=data["ability"],
            dc=data["dc"],
            is_death_save=data.get("is_death_save", False),
        )


class ContestSpec(Specification):
    """
    Opposed check: two entities roll against each other.
    
    The "candidate" is the initiator, and the opponent is in context.
    
    Example:
        # Grapple: Athletics vs Athletics or Acrobatics
        grapple = ContestSpec(
            initiator_skill="Athletics",
            defender_skills=["Athletics", "Acrobatics"],  # defender chooses
        )
    """
    
    def __init__(
        self,
        initiator_skill: str,
        defender_skills: list[str],
    ):
        self.initiator_skill = initiator_skill
        self.defender_skills = defender_skills
    
    @property
    def rule_id(self) -> str:
        defender = "/".join(self.defender_skills)
        return f"contest_{self.initiator_skill.lower()}_vs_{defender.lower()}"
    
    def is_satisfied_by(self, candidate: Any, context: dict[str, Any] | None = None) -> SpecResult:
        context = context or {}
        
        # Need both rolls
        initiator_roll = context.get("initiator_roll")
        defender_roll = context.get("defender_roll")
        defender = context.get("defender")
        defender_skill_used = context.get("defender_skill", self.defender_skills[0])
        
        if initiator_roll is None or defender_roll is None:
            return SpecResult(
                rule_id=self.rule_id,
                passed=False,
                message="Contest requires both initiator_roll and defender_roll",
                suggested_fix="Provide both rolls in context",
                tags=frozenset({"contest", "missing_roll"}),
            )
        
        # Get modifiers
        init_mod = self._get_modifier(candidate, self.initiator_skill)
        def_mod = self._get_modifier(defender, defender_skill_used) if defender else 0
        
        init_total = initiator_roll + init_mod
        def_total = defender_roll + def_mod
        
        # Initiator wins ties in 5e contests
        passed = init_total >= def_total
        
        return SpecResult(
            rule_id=self.rule_id,
            passed=passed,
            message=f"Contest: {self.initiator_skill} {init_total} vs {defender_skill_used} {def_total}",
            tags=frozenset({"contest", self.initiator_skill.lower()}),
            data={
                "initiator_skill": self.initiator_skill,
                "initiator_roll": initiator_roll,
                "initiator_modifier": init_mod,
                "initiator_total": init_total,
                "defender_skill": defender_skill_used,
                "defender_roll": defender_roll,
                "defender_modifier": def_mod,
                "defender_total": def_total,
            }
        )
    
    def _get_modifier(self, entity: Any, skill: str) -> int:
        if entity is None:
            return 0
        if hasattr(entity, "skill_modifiers"):
            return entity.skill_modifiers.get(skill, 0)
        if isinstance(entity, dict):
            return entity.get("skill_modifiers", {}).get(skill, 0)
        return 0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "ContestSpec",
            "initiator_skill": self.initiator_skill,
            "defender_skills": self.defender_skills,
        }

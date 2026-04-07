"""Data-driven choreography sequence definitions — no Qt imports.

Each combat action is decomposed into timed phases that the
:class:`ActionChoreographer` executes in order.  Phases are pure data;
the choreographer interprets them.

Follows the same frozen-dataclass pattern as :class:`ParticlePreset`
and :class:`AttackAnimConfig` in ``config.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Tuple


class ChoreographyPhase(Enum):
    """The four phases of a choreographed action."""
    INTENT = auto()      # Camera pan, actor highlight, announce
    APPROACH = auto()    # Movement toward target (lunge/projectile/channel)
    IMPACT = auto()      # Damage/miss resolution visuals
    AFTERMATH = auto()   # HP bar update, portrait swap, death effects


class EffectType(Enum):
    """Kind of visual/audio effect fired during a phase."""
    TOKEN_ANIM = auto()      # TokenAnimator call (lunge/shake/recoil)
    PARTICLE = auto()        # Spawn a ParticlePreset
    FLOATING_TEXT = auto()   # FloatingText with templated content
    SOUND = auto()           # UISoundManager.play()
    HIGHLIGHT = auto()       # Tile pulse_select
    UPDATE_HP = auto()       # Refresh initiative panel / HP displays


@dataclass(frozen=True)
class ChoreographyEffect:
    """A single visual/audio effect within a phase.

    :param effect_type: What kind of effect to fire.
    :param target: ``"attacker"`` or ``"defender"`` — which entity this applies to.
    :param params: Effect-specific parameters (template strings like
        ``"{damage}"`` are resolved at runtime).
    """
    effect_type: EffectType
    target: str = "defender"
    params: Dict[str, str] = field(default_factory=dict)

    def __hash__(self):
        return hash((self.effect_type, self.target, tuple(sorted(self.params.items()))))


@dataclass(frozen=True)
class PhaseStep:
    """A single phase in a choreographed action sequence.

    :param phase: Which choreography phase this step represents.
    :param duration_ms: How long this phase runs before the next starts.
    :param effects: Effects to fire simultaneously at the start of this phase.
    """
    phase: ChoreographyPhase
    duration_ms: int = 300
    effects: Tuple[ChoreographyEffect, ...] = ()


@dataclass(frozen=True)
class ChoreographySequence:
    """A complete choreographed action — an ordered list of phase steps.

    Built by the choreographer from an :class:`ActionResult`.
    Total duration = sum of all step durations.
    """
    name: str
    steps: Tuple[PhaseStep, ...] = ()

    @property
    def total_duration_ms(self) -> int:
        return sum(s.duration_ms for s in self.steps)


# ─── Built-in sequences ─────────────────────────────────────────────

MELEE_HIT = ChoreographySequence(
    name="melee_hit",
    steps=(
        PhaseStep(
            phase=ChoreographyPhase.INTENT,
            duration_ms=100,
            effects=(
                ChoreographyEffect(EffectType.HIGHLIGHT, "attacker"),
            ),
        ),
        PhaseStep(
            phase=ChoreographyPhase.APPROACH,
            duration_ms=250,
            effects=(
                ChoreographyEffect(EffectType.TOKEN_ANIM, "attacker",
                                   {"anim": "LUNGE"}),
            ),
        ),
        PhaseStep(
            phase=ChoreographyPhase.IMPACT,
            duration_ms=300,
            effects=(
                ChoreographyEffect(EffectType.TOKEN_ANIM, "defender",
                                   {"anim": "SHAKE"}),
                ChoreographyEffect(EffectType.PARTICLE, "defender",
                                   {"preset": "slash_sparks"}),
                ChoreographyEffect(EffectType.FLOATING_TEXT, "defender",
                                   {"text": "-{damage}", "color": "#c0392b",
                                    "size": "14"}),
                ChoreographyEffect(EffectType.SOUND, "defender",
                                   {"id": "attack", "category": "combat"}),
            ),
        ),
        PhaseStep(
            phase=ChoreographyPhase.AFTERMATH,
            duration_ms=200,
            effects=(
                ChoreographyEffect(EffectType.UPDATE_HP),
            ),
        ),
    ),
)

MELEE_CRIT = ChoreographySequence(
    name="melee_crit",
    steps=(
        PhaseStep(ChoreographyPhase.INTENT, 100, (
            ChoreographyEffect(EffectType.HIGHLIGHT, "attacker"),
        )),
        PhaseStep(ChoreographyPhase.APPROACH, 250, (
            ChoreographyEffect(EffectType.TOKEN_ANIM, "attacker",
                               {"anim": "LUNGE"}),
        )),
        PhaseStep(ChoreographyPhase.IMPACT, 300, (
            ChoreographyEffect(EffectType.TOKEN_ANIM, "defender",
                               {"anim": "SHAKE"}),
            ChoreographyEffect(EffectType.PARTICLE, "defender",
                               {"preset": "crit_burst"}),
            ChoreographyEffect(EffectType.FLOATING_TEXT, "defender",
                               {"text": "CRIT! -{damage}", "color": "#e8b84b",
                                "size": "18"}),
            ChoreographyEffect(EffectType.SOUND, "defender",
                               {"id": "crit", "category": "combat"}),
        )),
        PhaseStep(ChoreographyPhase.AFTERMATH, 200, (
            ChoreographyEffect(EffectType.UPDATE_HP),
        )),
    ),
)

MELEE_MISS = ChoreographySequence(
    name="melee_miss",
    steps=(
        PhaseStep(ChoreographyPhase.INTENT, 100, (
            ChoreographyEffect(EffectType.HIGHLIGHT, "attacker"),
        )),
        PhaseStep(ChoreographyPhase.APPROACH, 200, (
            ChoreographyEffect(EffectType.TOKEN_ANIM, "attacker",
                               {"anim": "LUNGE"}),
        )),
        PhaseStep(ChoreographyPhase.IMPACT, 200, (
            ChoreographyEffect(EffectType.FLOATING_TEXT, "defender",
                               {"text": "MISS", "color": "#6b5d47",
                                "size": "12"}),
            ChoreographyEffect(EffectType.SOUND, "defender",
                               {"id": "miss", "category": "combat"}),
        )),
    ),
)

SPELL_HIT = ChoreographySequence(
    name="spell_hit",
    steps=(
        PhaseStep(ChoreographyPhase.INTENT, 150, (
            ChoreographyEffect(EffectType.HIGHLIGHT, "attacker"),
            ChoreographyEffect(EffectType.SOUND, "attacker",
                               {"id": "spell", "category": "combat"}),
        )),
        PhaseStep(ChoreographyPhase.IMPACT, 350, (
            ChoreographyEffect(EffectType.TOKEN_ANIM, "defender",
                               {"anim": "SHAKE"}),
            ChoreographyEffect(EffectType.PARTICLE, "defender",
                               {"preset": "spell_flash"}),
            ChoreographyEffect(EffectType.FLOATING_TEXT, "defender",
                               {"text": "-{damage}", "color": "#7f77dd",
                                "size": "14"}),
        )),
        PhaseStep(ChoreographyPhase.AFTERMATH, 200, (
            ChoreographyEffect(EffectType.UPDATE_HP),
        )),
    ),
)

HEAL = ChoreographySequence(
    name="heal",
    steps=(
        PhaseStep(ChoreographyPhase.INTENT, 100, (
            ChoreographyEffect(EffectType.HIGHLIGHT, "attacker"),
        )),
        PhaseStep(ChoreographyPhase.IMPACT, 400, (
            ChoreographyEffect(EffectType.PARTICLE, "defender",
                               {"preset": "healing_aura"}),
            ChoreographyEffect(EffectType.FLOATING_TEXT, "defender",
                               {"text": "+{heal}", "color": "#4caf50",
                                "size": "14"}),
        )),
    ),
)

SIMPLE_ACTION = ChoreographySequence(
    name="simple",
    steps=(
        PhaseStep(ChoreographyPhase.INTENT, 100),
        PhaseStep(ChoreographyPhase.AFTERMATH, 100),
    ),
)

# Registry for lookup by name
SEQUENCE_REGISTRY: Dict[str, ChoreographySequence] = {
    "melee_hit": MELEE_HIT,
    "melee_crit": MELEE_CRIT,
    "melee_miss": MELEE_MISS,
    "spell_hit": SPELL_HIT,
    "heal": HEAL,
    "simple": SIMPLE_ACTION,
}

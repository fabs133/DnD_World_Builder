"""Data-driven animation and particle configuration — no Qt imports."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


# ─── Particle Taxonomy (stable contract — do not modify categories) ───

class ParticleCategory(Enum):
    """The 6 particle categories. Add presets, never new categories."""
    IMPACT   = auto()
    AMBIENT  = auto()
    TRAIL    = auto()
    RADIANT  = auto()
    STATUS   = auto()
    GAME     = auto()


class EmissionShape(Enum):
    """How particles are spawned spatially."""
    POINT    = auto()  # All from one point
    RING     = auto()  # Around a circle edge
    DISC     = auto()  # Random within a circle area
    CONE     = auto()  # Within an angular spread
    LINE     = auto()  # Along a line segment


class ParticleMotion(Enum):
    """How particles move after spawning."""
    RISE     = auto()  # Float upward (embers, motes)
    FALL     = auto()  # Drop downward (rain, snow, debris)
    EXPLODE  = auto()  # Radial outward burst
    DRIFT    = auto()  # Slow random wander
    ORBIT    = auto()  # Circle around center point
    FOLLOW   = auto()  # Trail behind a moving source
    STATIC   = auto()  # Stay in place, just fade


@dataclass(frozen=True)
class ParticlePreset:
    """
    Complete particle effect definition. Pure data, no Qt.

    This is the core building block — every visual effect in the system
    is expressed as a ParticlePreset + a ParticleCategory.
    """
    name: str
    category: ParticleCategory

    # Emission
    count: int = 10                     # Particles per burst (Impact) or max alive (continuous)
    emission_rate: float = 0.0          # Particles/sec for continuous emitters (0 = all at once)
    emission_shape: EmissionShape = EmissionShape.POINT
    emission_radius: float = 5.0        # Radius for RING/DISC shapes
    emission_angle: float = 360.0       # Spread angle for CONE shape

    # Appearance
    color_start: str = "#e8b84b"        # Color at birth
    color_end: str | None = None        # Color at death (None = same as start)
    size_start: float = 3.0             # Radius at birth
    size_end: float = 0.5               # Radius at death
    opacity_start: float = 0.8
    opacity_end: float = 0.0

    # Motion
    motion: ParticleMotion = ParticleMotion.EXPLODE
    speed: float = 2.0                  # Base speed (px/frame)
    speed_variance: float = 0.5         # Randomness in speed
    gravity: float = 0.0                # Downward pull per frame
    drag: float = 0.02                  # Speed reduction per frame (0-1)
    direction_deg: float = 0.0          # Base direction (0 = right, 90 = up)

    # Lifetime
    lifetime_ms: int = 400              # Per-particle lifetime
    lifetime_variance_ms: int = 100     # Randomness in lifetime

    # Rendering
    glow: bool = False                  # Draw with radial gradient (soft edge)
    layer: int = 999                    # Z-value on scene


# ─── Token Animation Types ───

class AnimationType(Enum):
    LUNGE    = auto()
    SHAKE    = auto()
    RECOIL   = auto()
    FLASH    = auto()
    PROJECTILE = auto()
    RADIAL   = auto()


@dataclass(frozen=True)
class AnimationConfig:
    """Configuration for a single token animation effect."""
    anim_type: AnimationType
    duration_ms: int = 300
    color: str = "#e8b84b"
    intensity: float = 1.0
    delay_ms: int = 0


@dataclass(frozen=True)
class AttackAnimConfig:
    """Full attack animation sequence (token anims + particle effects)."""
    attacker_anim: AnimationConfig = field(
        default_factory=lambda: AnimationConfig(AnimationType.LUNGE, 250)
    )
    defender_hit_anim: AnimationConfig = field(
        default_factory=lambda: AnimationConfig(AnimationType.SHAKE, 200, "#c0392b")
    )
    defender_miss_anim: AnimationConfig | None = None
    show_damage_number: bool = True
    show_miss_text: bool = True
    impact_preset: str = "slash_sparks"
    trail_preset: str | None = None


DEFAULT_MELEE_ATTACK = AttackAnimConfig()
DEFAULT_RANGED_ATTACK = AttackAnimConfig(
    attacker_anim=AnimationConfig(AnimationType.FLASH, 150, "#e8b84b"),
    defender_hit_anim=AnimationConfig(AnimationType.RECOIL, 200, "#c0392b"),
    impact_preset="arrow_puff",
    trail_preset="projectile_trail",
)
DEFAULT_SPELL_ATTACK = AttackAnimConfig(
    attacker_anim=AnimationConfig(AnimationType.FLASH, 200, "#7f77dd"),
    defender_hit_anim=AnimationConfig(AnimationType.SHAKE, 250, "#7f77dd"),
    impact_preset="spell_flash",
    trail_preset="magic_trail",
)

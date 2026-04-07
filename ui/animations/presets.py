"""
All particle presets organized by category.

To add a new effect: add a ParticlePreset here. Never add a new ParticleCategory.
"""

from ui.animations.config import (
    ParticlePreset, ParticleCategory, ParticleMotion, EmissionShape,
)


# ═══════════════════════════════════════════════════════════
# IMPACT — one-shot bursts, self-destruct
# ═══════════════════════════════════════════════════════════

SLASH_SPARKS = ParticlePreset(
    name="slash_sparks",
    category=ParticleCategory.IMPACT,
    count=12,
    emission_shape=EmissionShape.CONE,
    emission_angle=90.0,
    color_start="#e8b84b",
    color_end="#c0392b",
    size_start=2.5,
    size_end=0.5,
    motion=ParticleMotion.EXPLODE,
    speed=3.5,
    speed_variance=1.5,
    drag=0.04,
    lifetime_ms=350,
    glow=True,
)

ARROW_PUFF = ParticlePreset(
    name="arrow_puff",
    category=ParticleCategory.IMPACT,
    count=6,
    emission_shape=EmissionShape.POINT,
    color_start="#b8a88a",
    color_end="#6b5d47",
    size_start=2.0,
    size_end=3.0,
    motion=ParticleMotion.EXPLODE,
    speed=1.5,
    drag=0.06,
    lifetime_ms=300,
)

SPELL_FLASH = ParticlePreset(
    name="spell_flash",
    category=ParticleCategory.IMPACT,
    count=15,
    emission_shape=EmissionShape.RING,
    emission_radius=8.0,
    color_start="#7f77dd",
    color_end="#afa9ec",
    size_start=3.0,
    size_end=1.0,
    motion=ParticleMotion.EXPLODE,
    speed=2.0,
    drag=0.05,
    lifetime_ms=400,
    glow=True,
)

CRIT_BURST = ParticlePreset(
    name="crit_burst",
    category=ParticleCategory.IMPACT,
    count=20,
    emission_shape=EmissionShape.DISC,
    emission_radius=5.0,
    color_start="#e8b84b",
    color_end="#c9952a",
    size_start=3.5,
    size_end=0.5,
    motion=ParticleMotion.EXPLODE,
    speed=5.0,
    speed_variance=2.0,
    drag=0.03,
    lifetime_ms=500,
    glow=True,
)

DEBRIS = ParticlePreset(
    name="debris",
    category=ParticleCategory.IMPACT,
    count=8,
    emission_shape=EmissionShape.DISC,
    emission_radius=4.0,
    color_start="#888780",
    color_end="#5f5e5a",
    size_start=2.0,
    size_end=1.5,
    motion=ParticleMotion.EXPLODE,
    speed=3.0,
    gravity=0.15,
    drag=0.02,
    lifetime_ms=500,
)

TRAP_TRIGGER = ParticlePreset(
    name="trap_trigger",
    category=ParticleCategory.IMPACT,
    count=10,
    emission_shape=EmissionShape.RING,
    emission_radius=12.0,
    color_start="#c0392b",
    color_end="#8b2020",
    size_start=2.0,
    size_end=0.5,
    motion=ParticleMotion.RISE,
    speed=1.5,
    lifetime_ms=400,
    glow=True,
)


# ═══════════════════════════════════════════════════════════
# AMBIENT — continuous, tile-bound
# ═══════════════════════════════════════════════════════════

EMBERS = ParticlePreset(
    name="embers",
    category=ParticleCategory.AMBIENT,
    count=10,
    emission_rate=3.0,
    emission_shape=EmissionShape.DISC,
    emission_radius=18.0,
    color_start="#e8b84b",
    color_end="#c0392b",
    size_start=2.0,
    size_end=0.5,
    motion=ParticleMotion.RISE,
    speed=0.6,
    speed_variance=0.3,
    lifetime_ms=2000,
    lifetime_variance_ms=800,
    glow=True,
)

DUST_MOTES = ParticlePreset(
    name="dust_motes",
    category=ParticleCategory.AMBIENT,
    count=6,
    emission_rate=1.5,
    emission_shape=EmissionShape.DISC,
    emission_radius=20.0,
    color_start="#b8a88a",
    size_start=1.5,
    size_end=1.0,
    opacity_start=0.3,
    opacity_end=0.0,
    motion=ParticleMotion.DRIFT,
    speed=0.2,
    lifetime_ms=3000,
    lifetime_variance_ms=1000,
)

RAIN = ParticlePreset(
    name="rain",
    category=ParticleCategory.AMBIENT,
    count=15,
    emission_rate=8.0,
    emission_shape=EmissionShape.LINE,
    emission_radius=20.0,
    color_start="#85b7eb",
    size_start=1.0,
    size_end=1.0,
    opacity_start=0.5,
    motion=ParticleMotion.FALL,
    speed=4.0,
    speed_variance=1.0,
    lifetime_ms=600,
)

SWAMP_BUBBLES = ParticlePreset(
    name="swamp_bubbles",
    category=ParticleCategory.AMBIENT,
    count=4,
    emission_rate=0.8,
    emission_shape=EmissionShape.DISC,
    emission_radius=15.0,
    color_start="#97c459",
    size_start=2.0,
    size_end=3.5,
    opacity_start=0.4,
    opacity_end=0.0,
    motion=ParticleMotion.RISE,
    speed=0.3,
    lifetime_ms=1500,
)

SNOW = ParticlePreset(
    name="snow",
    category=ParticleCategory.AMBIENT,
    count=12,
    emission_rate=4.0,
    emission_shape=EmissionShape.LINE,
    emission_radius=20.0,
    color_start="#d3d1c7",
    size_start=2.0,
    size_end=1.5,
    opacity_start=0.6,
    motion=ParticleMotion.FALL,
    speed=1.0,
    speed_variance=0.5,
    lifetime_ms=2000,
    lifetime_variance_ms=500,
)

FOG = ParticlePreset(
    name="fog",
    category=ParticleCategory.AMBIENT,
    count=5,
    emission_rate=0.5,
    emission_shape=EmissionShape.DISC,
    emission_radius=25.0,
    color_start="#888780",
    size_start=8.0,
    size_end=12.0,
    opacity_start=0.15,
    opacity_end=0.0,
    motion=ParticleMotion.DRIFT,
    speed=0.1,
    lifetime_ms=5000,
)


# ═══════════════════════════════════════════════════════════
# TRAIL — follows moving source, dies with animation
# ═══════════════════════════════════════════════════════════

PROJECTILE_TRAIL = ParticlePreset(
    name="projectile_trail",
    category=ParticleCategory.TRAIL,
    count=8,
    emission_rate=20.0,
    emission_shape=EmissionShape.POINT,
    color_start="#e8b84b",
    color_end="#7a5a1a",
    size_start=2.0,
    size_end=0.5,
    motion=ParticleMotion.FOLLOW,
    speed=0.0,           # Stays where spawned, source moves away
    drag=0.0,
    lifetime_ms=300,
    glow=True,
)

MAGIC_TRAIL = ParticlePreset(
    name="magic_trail",
    category=ParticleCategory.TRAIL,
    count=10,
    emission_rate=25.0,
    emission_shape=EmissionShape.DISC,
    emission_radius=3.0,
    color_start="#afa9ec",
    color_end="#7f77dd",
    size_start=2.5,
    size_end=1.0,
    motion=ParticleMotion.DRIFT,
    speed=0.3,
    lifetime_ms=400,
    glow=True,
)

SWORD_ARC = ParticlePreset(
    name="sword_arc",
    category=ParticleCategory.TRAIL,
    count=6,
    emission_rate=30.0,
    emission_shape=EmissionShape.POINT,
    color_start="#d3d1c7",
    color_end="#888780",
    size_start=1.5,
    size_end=0.5,
    opacity_start=0.6,
    motion=ParticleMotion.FOLLOW,
    speed=0.0,
    lifetime_ms=200,
)

DASH_WIND = ParticlePreset(
    name="dash_wind",
    category=ParticleCategory.TRAIL,
    count=5,
    emission_rate=15.0,
    emission_shape=EmissionShape.LINE,
    emission_radius=8.0,
    color_start="#b8a88a",
    size_start=1.0,
    size_end=3.0,
    opacity_start=0.3,
    opacity_end=0.0,
    motion=ParticleMotion.STATIC,
    lifetime_ms=350,
)

BLOOD_DROPS = ParticlePreset(
    name="blood_drops",
    category=ParticleCategory.TRAIL,
    count=3,
    emission_rate=5.0,
    emission_shape=EmissionShape.POINT,
    color_start="#8b2020",
    color_end="#501313",
    size_start=1.5,
    size_end=1.0,
    motion=ParticleMotion.FALL,
    speed=1.0,
    gravity=0.2,
    lifetime_ms=500,
)


# ═══════════════════════════════════════════════════════════
# RADIANT — stationary patterned emitter, entity/tile-bound
# ═══════════════════════════════════════════════════════════

TORCH_FLAME = ParticlePreset(
    name="torch_flame",
    category=ParticleCategory.RADIANT,
    count=8,
    emission_rate=6.0,
    emission_shape=EmissionShape.POINT,
    color_start="#e8b84b",
    color_end="#c0392b",
    size_start=2.5,
    size_end=0.5,
    motion=ParticleMotion.RISE,
    speed=0.8,
    speed_variance=0.3,
    lifetime_ms=600,
    lifetime_variance_ms=200,
    glow=True,
)

MAGIC_CIRCLE = ParticlePreset(
    name="magic_circle",
    category=ParticleCategory.RADIANT,
    count=12,
    emission_rate=4.0,
    emission_shape=EmissionShape.RING,
    emission_radius=20.0,
    color_start="#7f77dd",
    color_end="#afa9ec",
    size_start=2.0,
    size_end=1.0,
    motion=ParticleMotion.ORBIT,
    speed=0.5,
    lifetime_ms=3000,
    glow=True,
)

HEALING_AURA = ParticlePreset(
    name="healing_aura",
    category=ParticleCategory.RADIANT,
    count=8,
    emission_rate=3.0,
    emission_shape=EmissionShape.DISC,
    emission_radius=15.0,
    color_start="#5dcaa5",
    color_end="#9fe1cb",
    size_start=2.0,
    size_end=1.0,
    motion=ParticleMotion.RISE,
    speed=0.4,
    lifetime_ms=1500,
    glow=True,
)

POISON_CLOUD = ParticlePreset(
    name="poison_cloud",
    category=ParticleCategory.RADIANT,
    count=6,
    emission_rate=2.0,
    emission_shape=EmissionShape.DISC,
    emission_radius=18.0,
    color_start="#97c459",
    color_end="#639922",
    size_start=5.0,
    size_end=8.0,
    opacity_start=0.2,
    opacity_end=0.0,
    motion=ParticleMotion.DRIFT,
    speed=0.15,
    lifetime_ms=2500,
)

PORTAL_SWIRL = ParticlePreset(
    name="portal_swirl",
    category=ParticleCategory.RADIANT,
    count=15,
    emission_rate=8.0,
    emission_shape=EmissionShape.RING,
    emission_radius=16.0,
    color_start="#7f77dd",
    color_end="#534ab7",
    size_start=2.0,
    size_end=0.5,
    motion=ParticleMotion.ORBIT,
    speed=1.5,
    lifetime_ms=1200,
    glow=True,
)

CAMPFIRE = ParticlePreset(
    name="campfire",
    category=ParticleCategory.RADIANT,
    count=12,
    emission_rate=5.0,
    emission_shape=EmissionShape.DISC,
    emission_radius=6.0,
    color_start="#ef9f27",
    color_end="#854f0b",
    size_start=2.5,
    size_end=1.0,
    motion=ParticleMotion.RISE,
    speed=0.5,
    speed_variance=0.2,
    lifetime_ms=1000,
    lifetime_variance_ms=400,
    glow=True,
)


# ═══════════════════════════════════════════════════════════
# STATUS — condition-driven, tracks entity token
# ═══════════════════════════════════════════════════════════

POISONED = ParticlePreset(
    name="poisoned",
    category=ParticleCategory.STATUS,
    count=5,
    emission_rate=2.0,
    emission_shape=EmissionShape.RING,
    emission_radius=14.0,
    color_start="#97c459",
    color_end="#639922",
    size_start=1.5,
    size_end=0.5,
    opacity_start=0.5,
    motion=ParticleMotion.RISE,
    speed=0.3,
    lifetime_ms=1500,
)

BLESSED = ParticlePreset(
    name="blessed",
    category=ParticleCategory.STATUS,
    count=6,
    emission_rate=2.5,
    emission_shape=EmissionShape.RING,
    emission_radius=14.0,
    color_start="#e8b84b",
    color_end="#c9952a",
    size_start=1.5,
    size_end=0.5,
    motion=ParticleMotion.RISE,
    speed=0.4,
    lifetime_ms=1200,
    glow=True,
)

ON_FIRE = ParticlePreset(
    name="on_fire",
    category=ParticleCategory.STATUS,
    count=8,
    emission_rate=5.0,
    emission_shape=EmissionShape.RING,
    emission_radius=12.0,
    color_start="#ef9f27",
    color_end="#c0392b",
    size_start=2.0,
    size_end=0.5,
    motion=ParticleMotion.RISE,
    speed=0.7,
    speed_variance=0.3,
    lifetime_ms=800,
    glow=True,
)

CONCENTRATING = ParticlePreset(
    name="concentrating",
    category=ParticleCategory.STATUS,
    count=8,
    emission_rate=3.0,
    emission_shape=EmissionShape.RING,
    emission_radius=16.0,
    color_start="#85b7eb",
    color_end="#b5d4f4",
    size_start=1.5,
    size_end=1.0,
    opacity_start=0.4,
    motion=ParticleMotion.ORBIT,
    speed=0.3,
    lifetime_ms=2500,
)

STUNNED = ParticlePreset(
    name="stunned",
    category=ParticleCategory.STATUS,
    count=5,
    emission_rate=2.0,
    emission_shape=EmissionShape.RING,
    emission_radius=10.0,
    color_start="#fac775",
    color_end="#e8b84b",
    size_start=2.0,
    size_end=1.5,
    motion=ParticleMotion.ORBIT,
    speed=1.2,
    lifetime_ms=1500,
)

FRIGHTENED = ParticlePreset(
    name="frightened",
    category=ParticleCategory.STATUS,
    count=4,
    emission_rate=1.5,
    emission_shape=EmissionShape.DISC,
    emission_radius=8.0,
    color_start="#888780",
    color_end="#5f5e5a",
    size_start=1.0,
    size_end=2.5,
    opacity_start=0.3,
    motion=ParticleMotion.RISE,
    speed=0.5,
    lifetime_ms=1200,
)

INVISIBLE = ParticlePreset(
    name="invisible",
    category=ParticleCategory.STATUS,
    count=4,
    emission_rate=1.0,
    emission_shape=EmissionShape.RING,
    emission_radius=14.0,
    color_start="#d3d1c7",
    size_start=1.0,
    size_end=0.5,
    opacity_start=0.15,
    opacity_end=0.0,
    motion=ParticleMotion.DRIFT,
    speed=0.2,
    lifetime_ms=2000,
)


# ═══════════════════════════════════════════════════════════
# GAME — UI-state-driven, rules/possibility/selection
# ═══════════════════════════════════════════════════════════

SELECTION_SHIMMER = ParticlePreset(
    name="selection_shimmer",
    category=ParticleCategory.GAME,
    count=6,
    emission_rate=3.0,
    emission_shape=EmissionShape.RING,
    emission_radius=16.0,
    color_start="#e8b84b",
    size_start=1.5,
    size_end=0.5,
    opacity_start=0.5,
    motion=ParticleMotion.RISE,
    speed=0.3,
    lifetime_ms=1000,
)

HOVER_GLOW = ParticlePreset(
    name="hover_glow",
    category=ParticleCategory.GAME,
    count=4,
    emission_rate=2.0,
    emission_shape=EmissionShape.RING,
    emission_radius=14.0,
    color_start="#b5d4f4",
    size_start=2.0,
    size_end=1.5,
    opacity_start=0.25,
    opacity_end=0.0,
    motion=ParticleMotion.STATIC,
    lifetime_ms=600,
)

REACHABLE_TILE = ParticlePreset(
    name="reachable_tile",
    category=ParticleCategory.GAME,
    count=3,
    emission_rate=1.5,
    emission_shape=EmissionShape.DISC,
    emission_radius=12.0,
    color_start="#5dcaa5",
    size_start=1.5,
    size_end=1.0,
    opacity_start=0.2,
    opacity_end=0.0,
    motion=ParticleMotion.STATIC,
    lifetime_ms=800,
)

AOE_PREVIEW = ParticlePreset(
    name="aoe_preview",
    category=ParticleCategory.GAME,
    count=10,
    emission_rate=5.0,
    emission_shape=EmissionShape.RING,
    emission_radius=0.0,   # Set dynamically based on spell radius
    color_start="#c0392b",
    color_end="#8b2020",
    size_start=1.5,
    size_end=0.5,
    opacity_start=0.35,
    motion=ParticleMotion.ORBIT,
    speed=0.6,
    lifetime_ms=1500,
)

ACTIVE_TURN = ParticlePreset(
    name="active_turn",
    category=ParticleCategory.GAME,
    count=6,
    emission_rate=2.0,
    emission_shape=EmissionShape.RING,
    emission_radius=18.0,
    color_start="#e8b84b",
    color_end="#c9952a",
    size_start=2.0,
    size_end=1.0,
    opacity_start=0.5,
    motion=ParticleMotion.ORBIT,
    speed=0.4,
    lifetime_ms=2000,
    glow=True,
)

THREAT_RANGE = ParticlePreset(
    name="threat_range",
    category=ParticleCategory.GAME,
    count=8,
    emission_rate=3.0,
    emission_shape=EmissionShape.RING,
    emission_radius=0.0,   # Set dynamically based on reach
    color_start="#c0392b",
    size_start=1.0,
    size_end=0.5,
    opacity_start=0.2,
    opacity_end=0.0,
    motion=ParticleMotion.ORBIT,
    speed=0.3,
    lifetime_ms=2000,
)

LEVEL_UP = ParticlePreset(
    name="level_up",
    category=ParticleCategory.GAME,
    count=25,
    emission_shape=EmissionShape.RING,
    emission_radius=20.0,
    color_start="#e8b84b",
    color_end="#fac775",
    size_start=3.0,
    size_end=1.0,
    motion=ParticleMotion.RISE,
    speed=2.0,
    speed_variance=1.0,
    lifetime_ms=800,
    glow=True,
)

ROUND_START = ParticlePreset(
    name="round_start",
    category=ParticleCategory.GAME,
    count=12,
    emission_shape=EmissionShape.LINE,
    emission_radius=30.0,
    color_start="#85b7eb",
    color_end="#b5d4f4",
    size_start=2.0,
    size_end=0.5,
    opacity_start=0.5,
    motion=ParticleMotion.RISE,
    speed=1.0,
    lifetime_ms=600,
)


# ═══════════════════════════════════════════════════════════
# REGISTRY — name -> preset lookup
# ═══════════════════════════════════════════════════════════

_ALL_PRESETS = [v for v in globals().values() if isinstance(v, ParticlePreset)]
PRESETS: dict[str, ParticlePreset] = {p.name: p for p in _ALL_PRESETS}

# Condition name -> status preset mapping (for CombatAnimator)
CONDITION_PRESETS: dict[str, str] = {
    "Poisoned":       "poisoned",
    "Blessed":        "blessed",
    "On Fire":        "on_fire",
    "Concentrating":  "concentrating",
    "Stunned":        "stunned",
    "Frightened":     "frightened",
    "Invisible":      "invisible",
}

def get_preset(name: str) -> ParticlePreset | None:
    """Look up a preset by name. Returns None if not found."""
    return PRESETS.get(name)

def get_presets_by_category(category: ParticleCategory) -> list[ParticlePreset]:
    """Get all presets in a category."""
    return [p for p in _ALL_PRESETS if p.category == category]

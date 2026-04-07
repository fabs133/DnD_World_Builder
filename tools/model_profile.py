"""Model-dependent generation configuration.

All values that change when swapping the underlying Stable Diffusion
model (checkpoint, VAE, resolution sweet spots, sampler settings,
negative prompt strength) are captured in a single :class:`ModelProfile`
dataclass.

Every generator module reads from the *active profile* via
:func:`get_active_profile`. To switch models, call
:func:`set_active_profile` with a different profile name or instance
before invoking any generation function.

Bundled profiles:
- ``sd15_dreamshaper`` — SD 1.5, DreamShaper 8 (current default)
- ``sd15_realistic_vision`` — SD 1.5, Realistic Vision 5.1 (textures)
- ``sdxl_juggernaut`` — SDXL, Juggernaut XL v9 (future upgrade)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelProfile:
    """Encapsulates every model-dependent generation parameter.

    All generator code should read from the active profile instead of
    using hardcoded values. This makes model swaps a one-line change.
    """

    # ── Identity ────────────────────────────────────────────
    name: str
    model_family: str              # "sd15", "sdxl", "flux"

    # ── Checkpoint / VAE ────────────────────────────────────
    checkpoint: str
    vae: str | None = None         # None = model's built-in VAE
    texture_checkpoint: str = ""   # alternative checkpoint for seamless textures
    upscaler: str = ""             # neural upscaler model name

    # ── Resolution ──────────────────────────────────────────
    base_resolution: tuple[int, int] = (768, 512)    # (w, h) scenery/transit tiles
    people_resolution: tuple[int, int] = (1024, 768)  # (w, h) narrative/boss tiles
    portrait_resolution: tuple[int, int] = (512, 512)  # character portraits
    map_panel_resolution: tuple[int, int] = (1024, 768)  # map overview panels

    # ── Sampler ─────────────────────────────────────────────
    sampler: str = "dpmpp_2m"
    scheduler: str = "karras"
    steps_scenery: int = 30
    steps_people: int = 35
    steps_portrait: int = 30
    steps_texture: int = 25
    cfg_scenery: float = 7.0
    cfg_people: float = 7.0
    cfg_portrait: float = 7.0
    cfg_texture: float = 7.0
    cfg_map: float = 7.5

    # ── Negative prompts ────────────────────────────────────
    # Models like Flux ignore negatives entirely; set to "" for those.
    supports_negative: bool = True
    negative_portrait: str = ""
    negative_scenery: str = ""
    negative_people: str = ""
    negative_terrain: str = ""
    negative_item: str = ""
    negative_map: str = ""

    # ── Capabilities ────────────────────────────────────────
    supports_regional: bool = True   # ConditioningSetMask works
    supports_img2img: bool = True    # for health-state variants
    supports_seamless_tile: bool = True  # SeamlessTile node

    # ── Regional prompting tuning ───────────────────────────
    regional_center_strength: float = 1.0
    regional_side_strength: float = 0.8
    regional_base_strength: float = 0.3


# ── Bundled profiles ──────────────────────────────────────────────────

# Common negative fragments reused across SD 1.5 profiles
_SD15_NEGATIVE_PORTRAIT = (
    "full body, legs, feet, standing, action pose, weapon in hand, "
    "holding weapon, full figure, below waist, "
    "modern clothing, anime, chibi, blurry, deformed, extra fingers, "
    "bad anatomy, text, watermark, logo, signature, ugly, duplicate, "
    "morbid, mutilated, out of frame, poorly drawn face, mutation, "
    "extra limbs, bad proportions, cloned face, gross proportions, "
    "malformed limbs, missing arms, missing legs, extra arms, "
    "fused fingers, too many fingers, long neck, cropped"
)
_SD15_NEGATIVE_ITEM = (
    "person, human, figure, character, body, hand, hands, fingers, arm, "
    "face, portrait, armor, clothing, warrior, soldier, holding, wielding, "
    "pedestal, platform, ground, floor, surface, table, stand, base, "
    "3d render, photograph, realistic, photorealistic, "
    "scenery, landscape, background detail, busy background, "
    "colored background, gradient background, "
    "text, watermark, blurry, multiple objects, cropped, out of frame, "
    "crossed, overlapping, pair, two weapons, dual"
)
_SD15_NEGATIVE_TERRAIN = (
    "person, object, horizon, sky, perspective, 3d, text, watermark, "
    "strong shadows, vignette, depth of field, bokeh, "
    "symmetrical, mirrored, kaleidoscope, repeating pattern, geometric, "
    "fractal, mandala, grid lines, border, frame"
)
_SD15_NEGATIVE_SCENERY = (
    "people, characters, text, watermark, modern, urban, bright cheerful, "
    "cartoon, anime, low quality, blurry"
)
_SD15_NEGATIVE_PEOPLE = (
    "bad anatomy, extra limbs, extra legs, two right legs, extra arms, "
    "missing limbs, missing arms, missing legs, malformed limbs, "
    "fused fingers, extra fingers, too many fingers, mutated hands, "
    "poorly drawn hands, bad hands, deformed hands, "
    "merged bodies, conjoined figures, cloned face, asymmetric eyes, "
    "mangled face, disfigured, mutation, deformed, ugly, "
    "duplicate, morbid, mutilated, poorly drawn face, "
    "people, characters, text, watermark, modern, urban, "
    "cartoon, anime, low quality, blurry, out of focus, "
    "grainy, jpeg artifacts"
)
_SD15_NEGATIVE_MAP = (
    "photorealistic, 3d render, modern, photograph, person close-up, "
    "portrait, text, watermark, blurry, low quality, anime, cartoon"
)

SD15_DREAMSHAPER = ModelProfile(
    name="SD 1.5 DreamShaper 8",
    model_family="sd15",
    checkpoint="dreamshaper_8.safetensors",
    vae="vae-ft-mse-840000-ema-pruned.safetensors",
    texture_checkpoint="Realistic_Vision_V5.1_fp16-no-ema.safetensors",
    upscaler="4x-UltraSharp.pth",
    base_resolution=(768, 512),
    people_resolution=(1024, 768),
    portrait_resolution=(512, 512),
    map_panel_resolution=(1024, 768),
    sampler="dpmpp_2m",
    scheduler="karras",
    steps_scenery=30,
    steps_people=35,
    steps_portrait=30,
    steps_texture=25,
    cfg_scenery=7.0,
    cfg_people=7.0,
    cfg_portrait=7.0,
    cfg_texture=7.0,
    cfg_map=7.5,
    supports_negative=True,
    negative_portrait=_SD15_NEGATIVE_PORTRAIT,
    negative_scenery=_SD15_NEGATIVE_SCENERY,
    negative_people=_SD15_NEGATIVE_PEOPLE,
    negative_terrain=_SD15_NEGATIVE_TERRAIN,
    negative_item=_SD15_NEGATIVE_ITEM,
    negative_map=_SD15_NEGATIVE_MAP,
    supports_regional=True,
    supports_img2img=True,
    supports_seamless_tile=True,
)

SD15_REALISTIC_VISION = ModelProfile(
    name="SD 1.5 Realistic Vision 5.1",
    model_family="sd15",
    checkpoint="Realistic_Vision_V5.1_fp16-no-ema.safetensors",
    vae="vae-ft-mse-840000-ema-pruned.safetensors",
    texture_checkpoint="Realistic_Vision_V5.1_fp16-no-ema.safetensors",
    upscaler="4x-UltraSharp.pth",
    base_resolution=(768, 512),
    people_resolution=(1024, 768),
    sampler="dpmpp_2m",
    scheduler="karras",
    cfg_scenery=7.0,
    cfg_people=7.5,
    supports_negative=True,
    negative_portrait=_SD15_NEGATIVE_PORTRAIT,
    negative_scenery=_SD15_NEGATIVE_SCENERY,
    negative_people=_SD15_NEGATIVE_PEOPLE,
    negative_terrain=_SD15_NEGATIVE_TERRAIN,
    negative_item=_SD15_NEGATIVE_ITEM,
    negative_map=_SD15_NEGATIVE_MAP,
)

# Placeholder for future SDXL upgrade — fill in checkpoint name when ready
SDXL_JUGGERNAUT = ModelProfile(
    name="SDXL Juggernaut XL v9",
    model_family="sdxl",
    checkpoint="juggernautXL_v9.safetensors",
    vae=None,  # SDXL models ship their own VAE
    upscaler="4x-UltraSharp.pth",
    base_resolution=(1024, 1024),
    people_resolution=(1216, 832),
    portrait_resolution=(768, 768),
    map_panel_resolution=(1024, 1024),
    sampler="dpmpp_2m",
    scheduler="karras",
    steps_scenery=25,
    steps_people=30,
    steps_portrait=25,
    cfg_scenery=5.0,        # SDXL prefers lower CFG
    cfg_people=5.5,
    cfg_portrait=5.0,
    cfg_map=6.0,
    supports_negative=True,
    # SDXL needs lighter negatives — anatomy is much better natively
    negative_portrait=(
        "anime, cartoon, blurry, deformed, extra fingers, bad anatomy, "
        "text, watermark, ugly, duplicate, out of frame"
    ),
    negative_scenery="cartoon, anime, low quality, blurry, text, watermark",
    negative_people=(
        "bad anatomy, extra limbs, deformed, merged bodies, "
        "cartoon, anime, blurry, text, watermark"
    ),
    negative_terrain=_SD15_NEGATIVE_TERRAIN,
    negative_item=_SD15_NEGATIVE_ITEM,
    negative_map=_SD15_NEGATIVE_MAP,
    supports_regional=True,
    supports_img2img=True,
    supports_seamless_tile=True,
    regional_center_strength=1.0,
    regional_side_strength=0.7,
    regional_base_strength=0.25,
)


# ── Active profile management ────────────────────────────────────────

_PROFILES: dict[str, ModelProfile] = {
    "sd15_dreamshaper": SD15_DREAMSHAPER,
    "sd15_realistic_vision": SD15_REALISTIC_VISION,
    "sdxl_juggernaut": SDXL_JUGGERNAUT,
}

_active_profile: ModelProfile = SD15_DREAMSHAPER


def get_active_profile() -> ModelProfile:
    """Return the currently active model profile."""
    return _active_profile


def set_active_profile(name_or_profile: str | ModelProfile) -> None:
    """Set the active model profile by name or instance."""
    global _active_profile
    if isinstance(name_or_profile, ModelProfile):
        _active_profile = name_or_profile
    elif name_or_profile in _PROFILES:
        _active_profile = _PROFILES[name_or_profile]
    else:
        available = ", ".join(sorted(_PROFILES.keys()))
        raise ValueError(
            f"Unknown profile {name_or_profile!r}. Available: {available}"
        )


def list_profiles() -> list[str]:
    """Return the names of all registered profiles."""
    return sorted(_PROFILES.keys())


def register_profile(name: str, profile: ModelProfile) -> None:
    """Register a custom profile for use with :func:`set_active_profile`."""
    _PROFILES[name] = profile

"""Per-preset audio effects chains using Spotify's Pedalboard library.

Each voice preset can have an optional effects chain that runs after
Chatterbox TTS generation and basic post-processing. Effects are designed
to reinforce the character archetype — ethereal spirits get reverb and
chorus, warlords get compression and presence, whispers get eerie delay.

Pedalboard is an optional dependency. If not installed, effects are
silently skipped (all voices still work, just without theming).
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Lazy-loaded to avoid import errors when pedalboard isn't installed
_effects_chains: Optional[dict] = None


def _build_effects_chains() -> dict:
    """Build the preset -> Pedalboard mapping. Called once on first use."""
    try:
        from pedalboard import (
            Pedalboard, Reverb, Chorus, Compressor,
            Gain, Delay, HighShelfFilter, LowShelfFilter,
        )
    except ImportError:
        logger.info("pedalboard not installed — voice effects disabled. "
                     "Install with: pip install pedalboard")
        return {}

    return {
        "ethereal": Pedalboard([
            Reverb(room_size=0.7, wet_level=0.4, damping=0.6),
            Chorus(rate_hz=0.5, depth=0.3, mix=0.3),
            Gain(gain_db=-2),
        ]),
        "creepy_whisper": Pedalboard([
            Reverb(room_size=0.5, wet_level=0.4, damping=0.5),
            Delay(delay_seconds=0.15, feedback=0.1, mix=0.2),
        ]),
        "warlord": Pedalboard([
            Compressor(threshold_db=-20, ratio=6),
            Gain(gain_db=3),
            Reverb(room_size=0.3, wet_level=0.2),
        ]),
        "mystic_elder": Pedalboard([
            Reverb(room_size=0.4, wet_level=0.25, damping=0.7),
            LowShelfFilter(cutoff_frequency_hz=300, gain_db=2),
        ]),
        "narrator": Pedalboard([
            Compressor(threshold_db=-25, ratio=4),
            Reverb(room_size=0.15, wet_level=0.1),
        ]),
        "grizzled_veteran": Pedalboard([
            HighShelfFilter(cutoff_frequency_hz=4000, gain_db=-3),
            Compressor(threshold_db=-20, ratio=3),
        ]),
        "barkeep": Pedalboard([
            Reverb(room_size=0.2, wet_level=0.15),
        ]),
        "scholar": Pedalboard([
            Reverb(room_size=0.25, wet_level=0.15),
            HighShelfFilter(cutoff_frequency_hz=3000, gain_db=2),
        ]),
        # roguish_trickster: no effects — clean, close, intimate
        # young_adventurer: no effects — bright and direct
    }


def apply_voice_effects(
    samples: np.ndarray,
    sample_rate: int,
    preset_name: str | None,
) -> np.ndarray:
    """Apply character-specific audio effects to TTS output.

    Args:
        samples: Mono float32 audio samples (already post-processed).
        sample_rate: Sample rate in Hz (typically 24000).
        preset_name: The voice preset ID (e.g., "ethereal", "warlord").
            If None or not found, returns samples unchanged.

    Returns:
        Processed audio samples as float32 numpy array.
    """
    global _effects_chains
    if _effects_chains is None:
        _effects_chains = _build_effects_chains()

    if not _effects_chains or not preset_name:
        return samples

    board = _effects_chains.get(preset_name)
    if board is None:
        return samples

    try:
        # Pedalboard needs a minimum buffer size for stable processing
        min_samples = sample_rate  # at least 1 second
        if len(samples) < min_samples:
            return samples

        # Pedalboard expects shape (channels, samples) as contiguous array
        shaped = np.ascontiguousarray(samples.reshape(1, -1), dtype=np.float32)
        effected = board(shaped, float(sample_rate))
        result = effected.flatten()

        # Re-normalize after effects (reverb can change peak levels)
        peak = np.abs(result).max()
        if peak > 0.01:
            result = result * (0.90 / peak)

        return result
    except Exception as e:
        logger.warning(f"Voice effects failed for preset '{preset_name}': {e}")
        return samples

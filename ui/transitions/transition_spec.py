"""Data-driven transition definitions.

Every view transition in the app is described by a TransitionSpec.
Pure Python — no Qt dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TransitionType(Enum):
    CUT = "cut"
    FADE = "fade"
    SLIDE = "slide"
    ZOOM = "zoom"
    CINEMATIC = "cinematic"


@dataclass(frozen=True)
class TransitionSpec:
    """Declarative definition of a view transition.

    :param name: Human-readable name.
    :param transition_type: Animation primitive.
    :param duration_ms: Total animation duration in milliseconds.
    :param easing: QEasingCurve name (e.g., ``"OutQuart"``).
    :param direction: Direction of motion.
    :param sound_id: Sound to play via UISoundManager (None for silent).
    :param sound_category: Volume channel for the sound.
    :param theme_before: Theme mode before transition (None = keep current).
    :param theme_after: Theme mode after transition (None = keep current).
    :param hold_black_ms: Duration of black screen pause (cinematic only).
    :param dust_particles: Whether to spawn particle effects.
    :param shake_frames: Number of shake frames before the cut.
    """

    name: str
    transition_type: TransitionType
    duration_ms: int
    easing: str = "OutQuart"
    direction: str = "up"
    sound_id: Optional[str] = None
    sound_category: str = "ui"
    theme_before: Optional[str] = None
    theme_after: Optional[str] = None
    hold_black_ms: int = 0
    dust_particles: bool = False
    shake_frames: int = 0

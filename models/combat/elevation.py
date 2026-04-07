"""Elevation constants and traversal evaluation for combat terrain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# Visual rendering
ELEVATION_PX = 8  # pixels of y-offset per elevation unit

# Movement thresholds
STEP_THRESHOLD = 1
CLIMB_THRESHOLD = 2
CLIMB_HIGH_THRESHOLD = 3
IMPASSABLE_THRESHOLD = 4
JUMP_DOWN_FREE = 1


class TraversalType(Enum):
    FLAT = "flat"
    STEP = "step"
    CLIMB = "climb"
    CLIMB_HARD = "climb_hard"
    JUMP_DOWN = "jump_down"
    IMPASSABLE = "impassable"


@dataclass
class TraversalInfo:
    """Result of evaluating traversal between two elevations."""
    traversal_type: TraversalType
    elevation_diff: int
    movement_cost_multiplier: float = 1.0
    requires_check: bool = False
    check_dc: int = 0
    fall_damage_dice: int = 0
    description: str = ""


def evaluate_traversal(
    from_elevation: int,
    to_elevation: int,
    has_climb_speed: bool = False,
    has_fly_speed: bool = False,
) -> TraversalInfo:
    """Evaluate how a combatant can move between two elevations."""
    diff = to_elevation - from_elevation
    abs_diff = abs(diff)

    if has_fly_speed:
        return TraversalInfo(
            traversal_type=TraversalType.FLAT,
            elevation_diff=diff,
            description="Flying over terrain",
        )

    if abs_diff == 0:
        return TraversalInfo(
            traversal_type=TraversalType.FLAT,
            elevation_diff=0,
            description="Level ground",
        )

    if abs_diff <= STEP_THRESHOLD:
        return TraversalInfo(
            traversal_type=TraversalType.STEP,
            elevation_diff=diff,
            description=f"Step {'up' if diff > 0 else 'down'} ({abs_diff} unit)",
        )

    # Going UP — climbing
    if diff > 0:
        if abs_diff >= IMPASSABLE_THRESHOLD:
            return TraversalInfo(
                traversal_type=TraversalType.IMPASSABLE,
                elevation_diff=diff,
                description=f"Too high to climb ({abs_diff} units)",
            )

        multiplier = 2.0 if abs_diff <= CLIMB_THRESHOLD else 3.0
        if has_climb_speed:
            multiplier = max(1.0, multiplier - 1.0)

        requires_check = abs_diff > CLIMB_THRESHOLD
        check_dc = 10 + (abs_diff - CLIMB_THRESHOLD) * 5 if requires_check else 0

        return TraversalInfo(
            traversal_type=(
                TraversalType.CLIMB if abs_diff <= CLIMB_THRESHOLD
                else TraversalType.CLIMB_HARD
            ),
            elevation_diff=diff,
            movement_cost_multiplier=multiplier,
            requires_check=requires_check,
            check_dc=check_dc,
            description=f"Climb up {abs_diff} units (x{multiplier} movement)",
        )

    # Going DOWN — jumping
    fall_dice = max(0, abs_diff - JUMP_DOWN_FREE)
    return TraversalInfo(
        traversal_type=TraversalType.JUMP_DOWN,
        elevation_diff=diff,
        fall_damage_dice=fall_dice,
        description=f"Jump down {abs_diff} units" + (
            f" ({fall_dice}d6 damage)" if fall_dice > 0 else ""
        ),
    )


def elevation_blocks_vision(
    viewer_elevation: int,
    blocker_elevation: int,
    target_elevation: int,
) -> bool:
    """Check if a tile blocks LoS based on elevation.

    A tile blocks if its elevation is higher than both viewer and target.
    """
    return blocker_elevation > viewer_elevation and blocker_elevation > target_elevation

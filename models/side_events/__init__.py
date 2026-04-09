import random
import re

from models.side_events.side_event_registry import (
    SideEvent,
    SideEventVariant,
    SIDE_EVENTS,
    SKILL_TO_ABILITY,
    get_event,
    get_interaction_type,
    is_terrain_compatible,
)

_DICE_RE = re.compile(r"^(\d+)d(\d+)([+-]\d+)?$")


def roll_dice(expr: str) -> int:
    """Roll dice from an expression like '1d6', '2d4+2', '1d8-1'.

    Returns the total rolled value (minimum 0).
    """
    m = _DICE_RE.match(expr.strip())
    if not m:
        return 0
    count, sides, bonus = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
    total = sum(random.randint(1, sides) for _ in range(count)) + bonus
    return max(0, total)

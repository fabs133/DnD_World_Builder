"""Combat participant wrapper around GameEntity."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional, Tuple

from core.constants import DEFAULT_SPEED_FT


class CombatantFaction(Enum):
    PLAYER = "player"
    ENEMY = "enemy"
    NEUTRAL = "neutral"
    ALLY = "ally"


@dataclass
class Combatant:
    """Runtime state for a single participant in combat.

    Wraps a GameEntity with combat-specific tracking: initiative,
    position, action economy, and conditions.
    """

    entity: Any  # GameEntity
    faction: CombatantFaction
    initiative: int = 0
    position: Tuple[int, int] = (0, 0)
    movement_remaining: int = 0
    action_used: bool = False
    bonus_action_used: bool = False
    reaction_used: bool = False
    surprised: bool = False
    conditions: List[str] = field(default_factory=list)
    concentration_spell: Optional[str] = None

    def reset_turn(self) -> None:
        """Reset per-turn resources at the start of this combatant's turn."""
        self.movement_remaining = getattr(self.entity, "speed", DEFAULT_SPEED_FT)
        self.action_used = False
        self.bonus_action_used = False
        self.reaction_used = False

    @property
    def name(self) -> str:
        return getattr(self.entity, "name", "Unknown")

    @property
    def is_conscious(self) -> bool:
        return self.hp > 0

    @property
    def hp(self) -> int:
        return getattr(self.entity, "hp", 0)

    @property
    def hp_max(self) -> int:
        return getattr(self.entity, "max_hp", 0)

    @property
    def health_category(self) -> str:
        """Player-visible health state (no exact numbers)."""
        if self.hp_max <= 0:
            return "unknown"
        ratio = self.hp / self.hp_max
        if ratio > 0.75:
            return "healthy"
        if ratio > 0.5:
            return "wounded"
        if ratio > 0.25:
            return "bloodied"
        if ratio > 0:
            return "near_death"
        return "unconscious"

    def to_dict(self) -> dict:
        return {
            "entity_name": self.name,
            "faction": self.faction.value,
            "initiative": self.initiative,
            "position": list(self.position),
            "movement_remaining": self.movement_remaining,
            "action_used": self.action_used,
            "bonus_action_used": self.bonus_action_used,
            "reaction_used": self.reaction_used,
            "surprised": self.surprised,
            "conditions": self.conditions,
            "concentration_spell": self.concentration_spell,
        }

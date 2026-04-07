"""Runtime combat encounter state."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from models.combat.combatant import Combatant, CombatantFaction


class CombatState(Enum):
    SETUP = "setup"
    INITIATIVE = "initiative"
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


@dataclass
class CombatInstance:
    """A live, mutable combat encounter.

    Created from an EncounterTemplate at runtime.
    """

    instance_id: str
    template_id: str
    template_name: str
    grid_width: int = 10
    grid_height: int = 10
    combatants: List[Combatant] = field(default_factory=list)
    current_turn_index: int = 0
    round_number: int = 1
    state: CombatState = CombatState.SETUP
    event_log: List[dict] = field(default_factory=list)

    @property
    def current_combatant(self) -> Optional[Combatant]:
        if not self.combatants or self.current_turn_index >= len(self.combatants):
            return None
        return self.combatants[self.current_turn_index]

    @property
    def active_combatants(self) -> List[Combatant]:
        return [c for c in self.combatants if c.is_conscious]

    @property
    def players(self) -> List[Combatant]:
        return [c for c in self.combatants if c.faction == CombatantFaction.PLAYER]

    @property
    def enemies(self) -> List[Combatant]:
        return [c for c in self.combatants if c.faction == CombatantFaction.ENEMY]

    def log_event(self, event_type: str, **kwargs) -> None:
        self.event_log.append({"type": event_type, **kwargs})

    def to_dict(self) -> dict:
        return {
            "instance_id": self.instance_id,
            "template_id": self.template_id,
            "template_name": self.template_name,
            "grid_width": self.grid_width,
            "grid_height": self.grid_height,
            "combatants": [c.to_dict() for c in self.combatants],
            "current_turn_index": self.current_turn_index,
            "round_number": self.round_number,
            "state": self.state.value,
            "event_log": self.event_log,
        }

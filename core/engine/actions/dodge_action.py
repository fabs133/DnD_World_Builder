"""Dodge action — impose disadvantage on attacks against you (D&D 5e)."""

from __future__ import annotations

from typing import Any

from models.flow.action.action import Action
from core.logger import app_logger


class DodgeAction(Action):
    """Focus on avoiding attacks until the start of your next turn.

    Per D&D 5e PHB p.192: "Until the start of your next turn, any
    attack roll made against you has disadvantage if you can see the
    attacker, and you make Dexterity saving throws with advantage."

    Sets ``actor.dodging = True``. AttackAction checks this flag
    and rolls with disadvantage when targeting a dodging entity.
    The flag is reset at the start of the actor's next turn by
    GameSession.
    """

    def validate(self, game_state) -> bool:
        if getattr(self.actor, "hp", 0) <= 0:
            self.execution_log.append("Actor is dead")
            return False
        return True

    def execute(self, game_state) -> dict:
        name = self.actor.name
        self.actor.dodging = True

        self.execution_log.append(f"{name} takes the Dodge action")
        app_logger.info(f"[Dodge] {name} is dodging until next turn")

        return {"action": "dodge", "actor": name}

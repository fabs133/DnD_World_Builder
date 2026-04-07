"""Disengage action — movement doesn't provoke opportunity attacks (D&D 5e)."""

from __future__ import annotations

from typing import Any

from models.flow.action.action import Action
from core.logger import app_logger


class DisengageAction(Action):
    """Carefully withdraw so movement doesn't provoke opportunity attacks.

    Per D&D 5e PHB p.192: "If you take the Disengage action, your
    movement doesn't provoke opportunity attacks for the rest of
    the turn."

    Sets ``actor.disengaging = True``. Any opportunity attack logic
    should check this flag before triggering. The flag is reset at
    the start of the actor's next turn by GameSession.
    """

    def validate(self, game_state) -> bool:
        if getattr(self.actor, "hp", 0) <= 0:
            self.execution_log.append("Actor is dead")
            return False
        return True

    def execute(self, game_state) -> dict:
        name = self.actor.name
        self.actor.disengaging = True

        self.execution_log.append(f"{name} takes the Disengage action")
        app_logger.info(f"[Disengage] {name} can move without provoking")

        return {"action": "disengage", "actor": name}

"""Dash action — double movement for this turn (D&D 5e)."""

from __future__ import annotations

from typing import Any

from models.flow.action.action import Action
from core.logger import app_logger


class DashAction(Action):
    """Use your action to gain extra movement equal to your speed.

    Per D&D 5e PHB p.192: "When you take the Dash action, you gain
    extra movement for the current turn. The increase equals your
    speed, after applying any modifiers."
    """

    def validate(self, game_state) -> bool:
        if getattr(self.actor, "hp", 0) <= 0:
            self.execution_log.append("Actor is dead")
            return False
        return True

    def execute(self, game_state) -> dict:
        name = self.actor.name
        from core.constants import DEFAULT_SPEED_FT
        speed = getattr(self.actor, "speed", DEFAULT_SPEED_FT)
        current = getattr(self.actor, "movement_remaining", 0)
        self.actor.movement_remaining = current + speed

        self.execution_log.append(
            f"{name} dashes (+{speed}ft movement, now {self.actor.movement_remaining}ft)"
        )
        app_logger.info(f"[Dash] {name}: +{speed}ft movement")

        return {
            "action": "dash",
            "actor": name,
            "extra_movement": speed,
            "movement_remaining": self.actor.movement_remaining,
        }

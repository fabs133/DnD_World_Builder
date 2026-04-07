"""Help action — grant advantage to an ally's next attack (D&D 5e)."""

from __future__ import annotations

from typing import Any

from models.flow.action.action import Action
from core.logger import app_logger


class HelpAction(Action):
    """Aid an ally, granting them advantage on their next attack roll.

    Per D&D 5e PHB p.192: "You can lend your aid to another creature
    in the completion of a task... the creature you aid gains advantage
    on the next ability check / attack roll."

    Sets ``target.has_advantage = True`` if a target ally is specified.
    AttackAction checks this flag and rolls with advantage. The flag
    is reset at the start of the helped entity's next turn by
    GameSession.
    """

    def __init__(self, actor: Any, target: Any = None):
        super().__init__(actor)
        self.target = target  # The ally being helped (optional)

    def validate(self, game_state) -> bool:
        if getattr(self.actor, "hp", 0) <= 0:
            self.execution_log.append("Actor is dead")
            return False
        return True

    def execute(self, game_state) -> dict:
        name = self.actor.name

        if self.target:
            self.target.has_advantage = True
            target_name = getattr(self.target, "name", "ally")
            self.execution_log.append(
                f"{name} helps {target_name} (advantage on next attack)"
            )
            app_logger.info(f"[Help] {name} grants advantage to {target_name}")
            return {"action": "help", "actor": name, "target": target_name}
        else:
            self.execution_log.append(f"{name} takes the Help action")
            app_logger.info(f"[Help] {name} takes the Help action")
            return {"action": "help", "actor": name}

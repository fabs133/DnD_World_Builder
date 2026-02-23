"""Explicit end-turn action (pass/do nothing)."""

from __future__ import annotations

from models.flow.action.action import Action


class EndTurnAction(Action):
    """Pass the turn without doing anything.

    Always valid, no-op execution.
    """

    def validate(self, game_state) -> bool:
        return True

    def execute(self, game_state) -> dict:
        name = getattr(self.actor, "name", "Unknown")
        self.execution_log.append(f"{name} ends turn")
        return {"action": "end_turn", "actor": name}

"""Parses LLM text output into Action objects."""

from __future__ import annotations

import re
import random
from typing import Any

from core.engine.game_state import GameState
from core.engine.actions.attack_action import AttackAction
from core.engine.actions.move_action import MoveAction
from core.engine.actions.end_turn_action import EndTurnAction


class ParseError(Exception):
    """Raised when LLM output cannot be parsed into an action."""

    def __init__(self, message: str, raw_output: str = ""):
        super().__init__(message)
        self.raw_output = raw_output


ACTION_PATTERN = re.compile(
    r"ACTION:\s*(\w+)"
    r"(?:\s+TARGET:\s*([\w_ ]+))?"
    r"(?:\s+POSITION:\s*(\d+)\s*,\s*(\d+))?",
    re.IGNORECASE,
)


class ActionParser:
    """Parses structured LLM output into Action objects.

    Expected format:
        ACTION: ATTACK TARGET: Goblin_1
        ACTION: MOVE POSITION: 3,4
        ACTION: END_TURN
    """

    def __init__(self, rng: random.Random | None = None):
        self._rng = rng or random.Random()

    def parse(
        self,
        llm_output: str,
        actor: Any,
        game_state: GameState,
        entities_by_name: dict[str, Any] | None = None,
    ) -> "Action":
        """Parse LLM output into an Action.

        Args:
            llm_output: Raw text from LLM.
            actor: The entity taking the action.
            game_state: Current game state for resolving references.
            entities_by_name: Optional lookup dict for mutable entity refs.

        Returns:
            Concrete Action subclass.

        Raises:
            ParseError: If output cannot be parsed.
        """
        match = ACTION_PATTERN.search(llm_output)
        if not match:
            raise ParseError(
                f"Could not find ACTION: pattern in output",
                raw_output=llm_output,
            )

        action_type = match.group(1).upper()
        target_name = match.group(2).strip() if match.group(2) else None
        pos_x = int(match.group(3)) if match.group(3) else None
        pos_y = int(match.group(4)) if match.group(4) else None

        if action_type == "ATTACK":
            if not target_name:
                raise ParseError(
                    "ATTACK requires TARGET: <name>",
                    raw_output=llm_output,
                )
            target = self._resolve_target(target_name, game_state, entities_by_name)
            return AttackAction(
                actor, target, damage_expr="1d6", to_hit_bonus=0, rng=self._rng
            )

        if action_type == "MOVE":
            if pos_x is None or pos_y is None:
                raise ParseError(
                    "MOVE requires POSITION: x,y",
                    raw_output=llm_output,
                )
            return MoveAction(actor, target_position=(pos_x, pos_y))

        if action_type in ("END_TURN", "ENDTURN", "END"):
            return EndTurnAction(actor)

        if action_type in ("DASH", "DODGE", "CAST_SPELL"):
            # For now, map unsupported actions to EndTurn
            return EndTurnAction(actor)

        raise ParseError(
            f"Unknown action type: {action_type}",
            raw_output=llm_output,
        )

    def _resolve_target(
        self,
        target_name: str,
        game_state: GameState,
        entities_by_name: dict[str, Any] | None = None,
    ) -> Any:
        """Find entity by name. Prefer mutable refs if available."""
        if entities_by_name and target_name in entities_by_name:
            return entities_by_name[target_name]

        # Fall back to snapshot (read-only, won't support HP mutation)
        snap = game_state.get_entity(target_name)
        if snap is not None:
            return snap

        # Try fuzzy match (underscores vs spaces)
        normalized = target_name.replace(" ", "_")
        if entities_by_name:
            for name, entity in entities_by_name.items():
                if name.replace(" ", "_") == normalized:
                    return entity

        raise ParseError(f"Target '{target_name}' not found in game state")

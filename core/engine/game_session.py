"""Headless game session orchestrator."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable

from core.logger import app_logger
from models.game_master import Gamemaster
from core.engine.game_state import GameState
from core.engine.initiative import InitiativeTracker
from core.engine.action_executor import ActionExecutor, ActionResult
from core.engine.input_adapter import InputAdapter


@dataclass
class GameSessionResult:
    """Result of a completed game session."""

    rounds_played: int
    final_state: GameState
    action_history: list[ActionResult] = field(default_factory=list)
    winner: str | None = None
    termination_reason: str = ""


class GameSession:
    """Orchestrates a complete headless game session.

    This is the main entry point for running games without UI.
    """

    def __init__(
        self,
        gamemaster: Gamemaster,
        adapters: dict[str, InputAdapter],
        seed: int | None = None,
        max_rounds: int = 100,
        ruleset: Any = None,
        on_round_start: Callable[[GameState], None] | None = None,
        on_turn_start: Callable[[GameState, str], None] | None = None,
        on_action_result: Callable[[ActionResult], None] | None = None,
        on_round_end: Callable[[GameState], None] | None = None,
    ):
        self._gm = gamemaster
        self._adapters = adapters
        self._seed = seed
        self._rng = random.Random(seed)
        self._max_rounds = max_rounds
        self._initiative = InitiativeTracker(seed=seed)
        self._executor = ActionExecutor(ruleset=ruleset)
        self._action_history: list[ActionResult] = []
        self._event_log: list[str] = []
        self._initialized = False

        self.on_round_start = on_round_start
        self.on_turn_start = on_turn_start
        self.on_action_result = on_action_result
        self.on_round_end = on_round_end

    def setup(self, entities: list | None = None) -> None:
        """Initialize entities, roll initiative, set up initial state."""
        if entities is not None:
            for entity in entities:
                if entity not in self._gm.game_entities:
                    self._gm.add_entity(entity)

        self._initiative.roll_initiative(self._gm.game_entities)
        self._event_log.append(
            f"Initiative order: {', '.join(self._initiative.get_order())}"
        )
        self._initialized = True

    def run(self) -> GameSessionResult:
        """Run the full game loop until termination condition."""
        if not self._initialized:
            self.setup()

        while not self.is_finished:
            self.run_one_round()

        return GameSessionResult(
            rounds_played=self._initiative.round_number - 1,
            final_state=self.get_state(),
            action_history=list(self._action_history),
            winner=self._determine_winner(),
            termination_reason=self._termination_reason(),
        )

    def run_one_round(self) -> list[ActionResult]:
        """Execute a single round (all entities take one turn)."""
        state = self.get_state()
        if self.on_round_start:
            self.on_round_start(state)

        round_results = []
        num_entities = len(self._initiative.get_order())

        for _ in range(num_entities):
            if self.is_finished:
                break
            result = self.run_one_turn()
            round_results.append(result)

        state = self.get_state()
        if self.on_round_end:
            self.on_round_end(state)

        return round_results

    def run_one_turn(self) -> ActionResult:
        """Execute a single entity's turn."""
        entry = self._initiative.current_entity
        if entry is None:
            return ActionResult(success=False, action=None, error="No entities in initiative")

        entity_name = entry.entity_name
        actor = entry.entity_ref
        state = self.get_state()

        if self.on_turn_start:
            self.on_turn_start(state, entity_name)

        # Reset movement budget for this turn
        speed = getattr(actor, "speed", 30)
        actor.movement_remaining = speed

        # Skip dead entities
        hp = getattr(actor, "hp", 0)
        if hp <= 0:
            self._event_log.append(f"{entity_name} is incapacitated, skipping turn.")
            self._initiative.next_turn()
            return ActionResult(
                success=True,
                action=None,
                execution_log=[f"{entity_name} skipped (incapacitated)"],
            )

        adapter = self._adapters.get(entity_name)
        if adapter is None:
            self._event_log.append(f"No adapter for {entity_name}, skipping turn.")
            self._initiative.next_turn()
            return ActionResult(
                success=True,
                action=None,
                execution_log=[f"{entity_name} skipped (no adapter)"],
            )

        available = self._executor.get_available_actions(actor, state)
        action = adapter.choose_action(entity_name, state, available)

        result = self._executor.execute(action, actor, state)
        self._action_history.append(result)

        if result.success:
            self._event_log.append(
                f"Round {self._initiative.round_number}: "
                f"{entity_name} executed {action.__class__.__name__}"
            )
        else:
            self._event_log.append(
                f"Round {self._initiative.round_number}: "
                f"{entity_name} failed {action.__class__.__name__}: {result.error}"
            )

        if self.on_action_result:
            self.on_action_result(result)

        self._initiative.next_turn()
        return result

    def get_state(self) -> GameState:
        """Create an immutable snapshot of current state."""
        current = self._initiative.current_entity
        current_name = current.entity_name if current else ""
        return GameState.from_gamemaster(
            self._gm,
            round_number=self._initiative.round_number,
            current_entity_name=current_name,
            initiative_order=self._initiative.get_order(),
            seed=self._seed or 0,
            event_log=self._event_log,
        )

    @property
    def is_finished(self) -> bool:
        """Check if game has reached a termination condition."""
        if not self._initialized:
            return False
        if self._initiative.round_number > self._max_rounds:
            return True
        return self._check_combat_over()

    def _check_combat_over(self) -> bool:
        """Check if all of one faction is dead."""
        players_alive = False
        enemies_alive = False
        for entity in self._gm.game_entities:
            hp = getattr(entity, "hp", 0)
            if hp <= 0:
                continue
            etype = getattr(entity, "entity_type", "").lower()
            if etype == "player":
                players_alive = True
            elif etype == "enemy":
                enemies_alive = True
        return not players_alive or not enemies_alive

    def _determine_winner(self) -> str | None:
        """Determine the winning faction."""
        players_alive = any(
            getattr(e, "hp", 0) > 0
            for e in self._gm.game_entities
            if getattr(e, "entity_type", "").lower() == "player"
        )
        enemies_alive = any(
            getattr(e, "hp", 0) > 0
            for e in self._gm.game_entities
            if getattr(e, "entity_type", "").lower() == "enemy"
        )
        if players_alive and not enemies_alive:
            return "player"
        if enemies_alive and not players_alive:
            return "enemy"
        return None

    def _termination_reason(self) -> str:
        if self._initiative.round_number > self._max_rounds:
            return "max_rounds_reached"
        winner = self._determine_winner()
        if winner:
            return f"{winner}_victory"
        return "unknown"

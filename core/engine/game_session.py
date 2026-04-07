"""Headless game session orchestrator."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable

from core.events import TRIGGER_TURN_START
from core.logger import app_logger
from models.entities.entity_type import EntityType
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
        fog_of_war: bool = False,
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

        # Fog of war
        self._fog_state = None
        if fog_of_war:
            from core.engine.fog_state import FogOfWarState
            self._fog_state = FogOfWarState()

        self.on_round_start = on_round_start
        self.on_turn_start = on_turn_start
        self.on_action_result = on_action_result
        self.on_round_end = on_round_end

    def set_adapter(self, entity_name: str, adapter) -> None:
        """Swap the input adapter for an entity mid-session."""
        self._adapters[entity_name] = adapter

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

        # Reset movement budget and per-turn combat flags
        from core.constants import DEFAULT_SPEED_FT
        speed = getattr(actor, "speed", DEFAULT_SPEED_FT)
        actor.movement_remaining = speed
        actor.dodging = False
        actor.disengaging = False
        actor.helping = False
        actor.has_advantage = False

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

        # Fire TURN_START event for trigger system
        from core.gameCreation.event_bus import EventBus
        EventBus.emit(TRIGGER_TURN_START, {
            "entity": actor,
            "position": getattr(actor, "position", None),
            "world": self._gm.world,
            "round_number": self._initiative.round_number,
        })

        adapter = self._adapters.get(entity_name)
        if adapter is None:
            self._event_log.append(f"No adapter for {entity_name}, skipping turn.")
            self._initiative.next_turn()
            return ActionResult(
                success=True,
                action=None,
                execution_log=[f"{entity_name} skipped (no adapter)"],
            )

        # D&D 5e two-phase turn: Movement + Action.
        # The adapter gets the full available list each call.  If it returns
        # a MoveAction we execute it and loop (movement phase).  If it
        # returns any other action we execute it once (action phase) and end.
        # This gives every entity BOTH movement AND an action each turn.
        actor.action_used = False
        last_result = None

        for _ in range(7):  # safety valve
            state = self.get_state()
            available = self._get_available_actions(actor)

            if not available or available == ["END_TURN"]:
                break

            action = adapter.choose_action(entity_name, state, available)
            action_cls = action.__class__.__name__

            # Defensive: ensure MoveAction never poisons the action flag
            if action_cls == "MoveAction":
                actor.action_used = False

            result = self._executor.execute(
                action, actor, state, context={"world": self._gm.world}
            )
            self._action_history.append(result)
            last_result = result

            if result.success:
                self._event_log.append(
                    f"Round {self._initiative.round_number}: "
                    f"{entity_name} executed {action_cls}"
                )
            else:
                self._event_log.append(
                    f"Round {self._initiative.round_number}: "
                    f"{entity_name} failed {action_cls}: {result.error}"
                )
                break

            if self.on_action_result:
                self.on_action_result(result)

            if action_cls == "MoveAction":
                # Movement phase: keep looping so entity can also take action
                if self._check_combat_over():
                    break
                continue

            # Non-move action executed — mark action used and end turn
            if action_cls in ("AttackAction", "DashAction", "DodgeAction",
                               "DisengageAction", "HelpAction", "SpellAction"):
                actor.action_used = True

            if action_cls == "EndTurnAction":
                break

            # After any non-move action, offer remaining movement
            # (D&D 5e: you can split movement around your action)
            if getattr(actor, "movement_remaining", 0) > 0:
                continue
            break

        if self._fog_state:
            self._update_fog()

        self._initiative.next_turn()
        return last_result or ActionResult(
            success=True, action=None,
            execution_log=[f"{entity_name} turn ended"],
        )

    def _update_fog(self) -> None:
        """Recalculate fog of war visibility from player-faction entities."""
        from core.engine.vision import compute_visible_tiles

        observers = []
        for entity in self._gm.game_entities:
            if getattr(entity, "hp", 0) <= 0:
                continue
            etype = getattr(entity, "entity_type", "")
            if etype in (EntityType.PLAYER, EntityType.ALLY, EntityType.COMPANION):
                pos = getattr(entity, "position", None)
                vision = getattr(entity, "vision_range", 12)
                if pos:
                    observers.append((pos, vision))

        if observers:
            visible = compute_visible_tiles(self._gm.world, observers)
            self._fog_state.update(visible)

    def _get_available_actions(self, actor) -> list[str]:
        """Determine what actions the actor can still take this turn."""
        if getattr(actor, "hp", 0) <= 0:
            return ["END_TURN"]

        available = []
        if getattr(actor, "movement_remaining", 0) > 0:
            available.append("MOVE")
        if not getattr(actor, "action_used", False):
            available.extend(["ATTACK", "DASH", "DODGE", "DISENGAGE", "HELP", "CAST_SPELL"])
        available.append("END_TURN")
        return available

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
            etype = getattr(entity, "entity_type", "")
            if etype == EntityType.PLAYER:
                players_alive = True
            elif etype == EntityType.ENEMY:
                enemies_alive = True
        return not players_alive or not enemies_alive

    def _determine_winner(self) -> str | None:
        """Determine the winning faction."""
        players_alive = any(
            getattr(e, "hp", 0) > 0
            for e in self._gm.game_entities
            if getattr(e, "entity_type", "") == EntityType.PLAYER
        )
        enemies_alive = any(
            getattr(e, "hp", 0) > 0
            for e in self._gm.game_entities
            if getattr(e, "entity_type", "") == EntityType.ENEMY
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

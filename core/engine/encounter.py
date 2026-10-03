"""Interactive encounter controller: the single source of turn order.

:class:`Encounter` is the push-model counterpart of
:class:`~core.engine.game_session.GameSession`. Instead of pulling actions
from input adapters in a loop, callers (the GUI, the multiplayer host)
submit actions for the current entity and advance turns explicitly.

Both share the same rules: turn order comes from
:class:`~core.engine.initiative.InitiativeTracker` and actions are validated
and executed by :class:`~core.engine.action_executor.ActionExecutor`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from core.engine.action_executor import ActionExecutor, ActionResult
from core.engine.actions.end_turn_action import EndTurnAction
from core.engine.initiative import InitiativeTracker
from core.gameCreation.event_bus import EventBus
from core.logger import app_logger

#: Trigger event type fired when an entity's turn begins (selectable in the trigger editor).
TRIGGER_TURN_START = "TURN_START"
#: Internal EventBus events, consumed by the network bridges.
TURN_STARTED = "turn_started"
ROUND_STARTED = "round_started"

#: Movement budget in feet for entities without a ``speed`` attribute (matches GameSession).
DEFAULT_SPEED = 30


@dataclass(frozen=True)
class TurnInfo:
    """Whose turn it is. ``entity_name`` is ``None`` when no encounter is running."""

    entity_name: str | None
    round_number: int


class EncounterError(Exception):
    """Raised when an action is submitted out of turn or with no encounter running."""


class Encounter:
    """Owns initiative and turn progression for one encounter.

    :param gamemaster: Provides ``game_entities`` and ``world``.
    :param seed: Seed for initiative rolls (``None`` for random).
    :param executor: Action executor; defaults to one without a ruleset.
    """

    def __init__(self, gamemaster: Any, seed: int | None = None, executor: ActionExecutor | None = None):
        self._gm = gamemaster
        self._tracker = InitiativeTracker(seed=seed)
        self._executor = executor or ActionExecutor()
        self._active = False
        self._listeners: list[Callable[[TurnInfo], None]] = []

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def round_number(self) -> int:
        return self._tracker.round_number

    @property
    def current_entity_name(self) -> str | None:
        entry = self._tracker.current_entity if self._active else None
        return entry.entity_name if entry else None

    @property
    def current_entity(self) -> Any:
        entry = self._tracker.current_entity if self._active else None
        return entry.entity_ref if entry else None

    def turn_info(self) -> TurnInfo:
        return TurnInfo(self.current_entity_name, self.round_number)

    def order(self) -> list[dict]:
        """Initiative order as plain dicts (name, roll, hp, max_hp, entity_type)."""
        if not self._active:
            return []
        return [
            {
                "name": e.entity_name,
                "roll": e.roll,
                "hp": getattr(e.entity_ref, "hp", None),
                "max_hp": getattr(e.entity_ref, "max_hp", None),
                "entity_type": _entity_type_name(e.entity_ref),
            }
            for e in self._tracker.entries()
        ]

    def add_listener(self, callback: Callable[[TurnInfo], None]) -> None:
        """Call ``callback(TurnInfo)`` whenever the turn changes or the encounter starts/ends."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[TurnInfo], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, entities: list | None = None) -> list[dict]:
        """Roll initiative and begin round 1.

        :param entities: Participants; defaults to all of the gamemaster's entities.
        :return: The initiative order (see :meth:`order`).
        :raises EncounterError: If there are no participants.
        """
        participants = list(entities if entities is not None else self._gm.game_entities)
        if not participants:
            raise EncounterError("Cannot start an encounter without entities")
        self._tracker.roll_initiative(participants)
        self._active = True
        app_logger.info(f"[Encounter] Started. Order: {', '.join(self._tracker.get_order())}")
        EventBus.emit(ROUND_STARTED, {"round": self.round_number})
        self._begin_turn()
        return self.order()

    def end(self) -> None:
        """Stop the encounter and clear initiative."""
        self._tracker.reset()
        self._active = False
        app_logger.info("[Encounter] Ended.")
        self._notify()

    def next_turn(self) -> TurnInfo:
        """Advance to the next entity, starting a new round when the order wraps."""
        self._require_active()
        previous_round = self.round_number
        self._tracker.next_turn()
        if self.round_number != previous_round:
            EventBus.emit(ROUND_STARTED, {"round": self.round_number})
        self._begin_turn()
        return self.turn_info()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def submit(self, actor_name: str, action: Any, game_state: Any = None) -> ActionResult:
        """Validate and execute ``action`` for the current entity.

        An :class:`EndTurnAction` advances the turn after it executes successfully.

        :raises EncounterError: If no encounter is running or it is not ``actor_name``'s turn.
        """
        self._require_active()
        if actor_name != self.current_entity_name:
            raise EncounterError(f"It is {self.current_entity_name}'s turn, not {actor_name}'s")
        result = self._executor.execute(action, self.current_entity, game_state)
        if result.success and isinstance(action, EndTurnAction):
            self.next_turn()
        return result

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _begin_turn(self) -> None:
        actor = self.current_entity
        if actor is not None:
            actor.movement_remaining = getattr(actor, "speed", DEFAULT_SPEED)
        world = getattr(self._gm, "world", None)
        turn_manager = getattr(world, "turn_manager", None)
        if turn_manager is not None:
            turn_manager.next_turn()  # drives trigger cooldowns and scheduled callbacks
        data = {"entity": self.current_entity_name, "round": self.round_number, "world": world}
        EventBus.emit(TURN_STARTED, data)
        EventBus.emit(TRIGGER_TURN_START, data)
        self._notify()

    def _notify(self) -> None:
        info = self.turn_info()
        for callback in list(self._listeners):
            callback(info)

    def _require_active(self) -> None:
        if not self._active:
            raise EncounterError("No encounter is running")


def _entity_type_name(entity: Any) -> str:
    """Entity type as a lowercase string, accepting both enums and plain strings."""
    entity_type = getattr(entity, "entity_type", "")
    return str(getattr(entity_type, "value", entity_type)).lower()

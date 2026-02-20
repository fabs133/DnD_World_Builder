# core/gameCreation/turn_system.py

from core.logger import app_logger
from core.gameCreation.event_bus import EventBus
from .combat_system import CombatSystem
from .action.action_validator import ActionValidator
from models.flow.reaction.reaction_queue import ReactionQueue

class TurnSystem:
    """
    Manages the turn order and round progression for a set of entities.

    Attributes
    ----------
    entities : list
        The list of entities participating in the turn system.
    current_turn : int
        The index of the entity whose turn it is.
    round_number : int
        The current round number.
    _scheduled : list
        Internal queue of scheduled callbacks.
    """

    def __init__(self, entities):
        """
        Initialize the TurnSystem.

        Parameters
        ----------
        entities : list
            The entities participating in the turn system.
        """
        self.entities = entities
        self.current_turn = 0
        self.round_number = 1

        # New: queue of (fire_round, callback, data)
        self._scheduled = []

    def schedule_in(self, turns: int, callback, data=None):
        """
        Schedule a callback to run after a certain number of turns.

        Parameters
        ----------
        turns : int
            Number of turns to wait before firing the callback.
            If 0, fires at the end of the current turn.
        callback : callable
            The function to call.
        data : any, optional
            Data to pass to the callback.
        """
        target_round = self.round_number + turns
        self._scheduled.append((target_round, callback, data))

    def _dispatch_scheduled(self):
        """
        Run all callbacks whose target round is less than or equal to the current round number.
        """
        to_run, self._scheduled = (
            [entry for entry in self._scheduled if entry[0] <= self.round_number],
            [entry for entry in self._scheduled if entry[0] > self.round_number]
        )
        for _, cb, data in to_run:
            cb(data)

    def start_round(self):
        """
        Start a new round, dispatching any scheduled events for this round.
        """
        app_logger.info(f"Round {self.round_number} starts!")
        # dispatch any events scheduled at the start of this round
        self._dispatch_scheduled()
        self.current_turn = 0
        self.round_number += 1

    def next_turn(self):
        """
        Advance to the next entity's turn.
        """
        self.current_turn = (self.current_turn + 1) % len(self.entities)
        current_entity = self.entities[self.current_turn]
        app_logger.info(f"It is now {current_entity.name}'s turn.")

    def execute_turn(self):
        """
        Execute the current entity's turn, including action validation,
        event emission, and reaction resolution.
        """
        current_entity = self.entities[self.current_turn]
        proposed_action = current_entity.decide_action()
        if ActionValidator.validate(proposed_action):
            EventBus.emit("ACTION_PROPOSED", proposed_action)

        if not ReactionQueue.blocked():
            proposed_action.execute()
            EventBus.emit("ACTION_EXECUTED", proposed_action)
        else:
            ReactionQueue.resolve()

        # End‐of‐turn: dispatch any events scheduled exactly for this round
        self._dispatch_scheduled()
        self.end_turn()

    def end_turn(self):
        """
        End the current entity's turn and advance to the next turn.
        """
        app_logger.info(f"{self.entities[self.current_turn].name}'s turn ends.")
        self.next_turn()

    # … rest of your methods unchanged …

"""Abstract input adapter for pluggable player control."""

from __future__ import annotations

from abc import ABC, abstractmethod

from models.flow.action.action import Action
from core.engine.game_state import GameState


class InputAdapter(ABC):
    """ABC for all player input sources.

    Implementations: TestAdapter, CLIAdapter, AIAdapter.
    """

    @abstractmethod
    def choose_action(
        self,
        entity_name: str,
        game_state: GameState,
        available_actions: list[str],
    ) -> Action:
        """Given the current game state and legal actions, return the chosen Action."""
        ...

    @abstractmethod
    def choose_target(
        self,
        entity_name: str,
        game_state: GameState,
        valid_targets: list[str],
    ) -> str:
        """Choose a target entity name."""
        ...

    @abstractmethod
    def choose_movement(
        self,
        entity_name: str,
        game_state: GameState,
        valid_positions: list[tuple[int, int]],
    ) -> tuple[int, int]:
        """Choose a position to move to."""
        ...


class TestAdapter(InputAdapter):
    """Pre-scripted adapter for deterministic testing.

    Feed it a sequence of actions/targets/positions and it replays them.
    """

    def __init__(
        self,
        action_sequence: list[Action] | None = None,
        target_sequence: list[str] | None = None,
        movement_sequence: list[tuple[int, int]] | None = None,
    ):
        self._actions = list(action_sequence or [])
        self._targets = list(target_sequence or [])
        self._movements = list(movement_sequence or [])
        self._action_index = 0
        self._target_index = 0
        self._movement_index = 0

    def choose_action(
        self,
        entity_name: str,
        game_state: GameState,
        available_actions: list[str],
    ) -> Action:
        if self._action_index >= len(self._actions):
            raise IndexError(
                f"TestAdapter ran out of scripted actions at index {self._action_index} "
                f"for entity {entity_name}"
            )
        action = self._actions[self._action_index]
        self._action_index += 1
        return action

    def choose_target(
        self,
        entity_name: str,
        game_state: GameState,
        valid_targets: list[str],
    ) -> str:
        if self._target_index >= len(self._targets):
            raise IndexError(
                f"TestAdapter ran out of scripted targets at index {self._target_index}"
            )
        target = self._targets[self._target_index]
        self._target_index += 1
        return target

    def choose_movement(
        self,
        entity_name: str,
        game_state: GameState,
        valid_positions: list[tuple[int, int]],
    ) -> tuple[int, int]:
        if self._movement_index >= len(self._movements):
            raise IndexError(
                f"TestAdapter ran out of scripted movements at index {self._movement_index}"
            )
        pos = self._movements[self._movement_index]
        self._movement_index += 1
        return pos

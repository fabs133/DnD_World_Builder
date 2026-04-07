"""Input adapter that bridges PyQt5 UI signals to the GameSession turn loop.

Instead of blocking (which would freeze the UI), this adapter uses a
request/response signal pattern:

1. GameSession calls choose_action() on the player's turn
2. UIInputAdapter emits ``action_requested`` with available actions
3. The UI shows buttons and waits for a click
4. The click calls ``submit_action()`` which stores the choice
5. choose_action() returns the stored action

The blocking wait uses QEventLoop so the Qt main loop continues to
process events (repaints, button clicks) while waiting.
"""

from __future__ import annotations

from typing import Any

from PyQt5.QtCore import QObject, QEventLoop, pyqtSignal

class UIInputAdapter(QObject):
    """Bridges Qt UI clicks to the InputAdapter interface.

    Implements the same choose_action / choose_target / choose_movement
    methods as InputAdapter via duck typing (cannot inherit both QObject
    and ABC due to metaclass conflict).

    Signals:
        action_requested(str, object, list):
            (entity_name, game_state, available_actions)
            Emitted when the engine needs a player decision.
        target_requested(str, object, list):
            (entity_name, game_state, valid_targets)
        movement_requested(str, object, list):
            (entity_name, game_state, valid_positions)
    """

    action_requested = pyqtSignal(str, object, list)
    target_requested = pyqtSignal(str, object, list)
    movement_requested = pyqtSignal(str, object, list)

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        self._pending_action = None
        self._pending_target = None
        self._pending_movement = None
        self._loop: QEventLoop | None = None

    # ------------------------------------------------------------------
    # InputAdapter interface
    # ------------------------------------------------------------------

    def choose_action(self, entity_name: str, game_state: Any,
                      available_actions: list[str]) -> Any:
        self._pending_action = None
        self.action_requested.emit(entity_name, game_state, available_actions)
        # Spin a local event loop so Qt keeps processing while we wait
        self._loop = QEventLoop()
        self._loop.exec_()
        return self._pending_action

    def choose_target(self, entity_name: str, game_state: Any,
                      valid_targets: list[str]) -> str:
        self._pending_target = None
        self.target_requested.emit(entity_name, game_state, valid_targets)
        self._loop = QEventLoop()
        self._loop.exec_()
        return self._pending_target

    def choose_movement(self, entity_name: str, game_state: Any,
                        valid_positions: list[tuple[int, int]]) -> tuple[int, int]:
        self._pending_movement = None
        self.movement_requested.emit(entity_name, game_state, valid_positions)
        self._loop = QEventLoop()
        self._loop.exec_()
        return self._pending_movement

    # ------------------------------------------------------------------
    # Slots called by the UI
    # ------------------------------------------------------------------

    def submit_action(self, action) -> None:
        """Called by the UI when the player clicks an action button."""
        self._pending_action = action
        if self._loop and self._loop.isRunning():
            self._loop.quit()

    def submit_target(self, target_name: str) -> None:
        self._pending_target = target_name
        if self._loop and self._loop.isRunning():
            self._loop.quit()

    def submit_movement(self, position: tuple[int, int]) -> None:
        self._pending_movement = position
        if self._loop and self._loop.isRunning():
            self._loop.quit()

    def cancel(self) -> None:
        """Force-quit the waiting loop (e.g. when closing the dialog)."""
        # Submit a sentinel so the session doesn't hang
        self._pending_action = _CancelAction()
        self._pending_target = ""
        self._pending_movement = (0, 0)
        if self._loop and self._loop.isRunning():
            self._loop.quit()


class _CancelAction:
    """Lightweight sentinel action returned when the UI is cancelled.

    Quacks enough like an Action for GameSession to handle it gracefully.
    """

    actor = None
    execution_log = []

    def validate(self, game_state) -> bool:
        return True

    def execute(self, game_state) -> dict:
        return {"description": "Turn cancelled."}

    @property
    def __class_name__(self):
        return "EndTurnAction"

    class __class__:
        __name__ = "EndTurnAction"

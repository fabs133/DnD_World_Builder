"""Movement action for repositioning on the grid."""

from __future__ import annotations

from typing import Any

from models.flow.action.action import Action
from core.logger import app_logger


class MoveAction(Action):
    """Move an entity to a new tile position.

    Args:
        actor: The entity moving.
        target_position: (x, y) destination.
        world_tile_manager: The tile manager for validation and state update.
    """

    def __init__(
        self,
        actor: Any,
        target_position: tuple[int, int],
        world_tile_manager: Any = None,
    ):
        super().__init__(actor)
        self.target_position = target_position
        self._tile_manager = world_tile_manager

    def validate(self, game_state) -> bool:
        if getattr(self.actor, "hp", 0) <= 0:
            self.execution_log.append("Actor is dead")
            return False
        if self._tile_manager and not self._tile_manager.is_valid_tile(
            self.target_position[0], self.target_position[1]
        ):
            self.execution_log.append(f"Invalid tile {self.target_position}")
            return False
        if self._tile_manager and self._tile_manager.is_blocking(
            self.target_position[0], self.target_position[1]
        ):
            self.execution_log.append(
                f"Tile {self.target_position} is blocked"
            )
            return False

        # Occupancy check: reject moves to tiles occupied by other alive entities
        for snap in getattr(game_state, "entities", ()):
            if snap.name == self.actor.name:
                continue
            if not getattr(snap, "is_alive", True):
                continue
            if snap.position == self.target_position:
                self.execution_log.append(
                    f"Tile {self.target_position} is occupied by {snap.name}"
                )
                return False

        # Pathfinder validation: check a walkable path exists
        if self._tile_manager:
            from core.engine.pathfinder import find_path, path_cost

            start = getattr(self.actor, "position", None)
            if start and start != self.target_position:
                path = find_path(start, self.target_position, self._tile_manager)
                if path is None:
                    self.execution_log.append(
                        f"No path from {start} to {self.target_position}"
                    )
                    return False

                # Check movement budget: prefer movement_remaining (per-turn),
                # fall back to speed (total).
                speed = getattr(self.actor, "movement_remaining", None)
                if speed is None:
                    speed = getattr(self.actor, "speed", None)
                if speed is not None:
                    cost = path_cost(path, self._tile_manager)
                    if cost > speed:
                        self.execution_log.append(
                            f"Path cost {cost}ft exceeds speed {speed}ft"
                        )
                        return False

        # Without tile_manager, still check movement budget
        if not self._tile_manager:
            start = getattr(self.actor, "position", None)
            if start and start != self.target_position:
                speed = getattr(self.actor, "movement_remaining", None)
                if speed is None:
                    speed = getattr(self.actor, "speed", None)
                if speed is not None:
                    dx = abs(self.target_position[0] - start[0])
                    dy = abs(self.target_position[1] - start[1])
                    cost = max(dx, dy) * 5  # 5ft per tile
                    if cost > speed:
                        self.execution_log.append(
                            f"Move cost {cost}ft exceeds speed {speed}ft"
                        )
                        return False

        return True

    def execute(self, game_state) -> dict:
        actor_name = self.actor.name
        old_pos = getattr(self.actor, "position", (0, 0))

        if self._tile_manager:
            self._tile_manager.move_entity(
                self.actor, self.target_position[0], self.target_position[1]
            )
        else:
            app_logger.debug("No tile_manager; setting position directly")
            self.actor.position = self.target_position

        # Deduct movement budget
        if self._tile_manager and hasattr(self.actor, "movement_remaining"):
            from core.engine.pathfinder import find_path, path_cost
            path = find_path(old_pos, self.target_position, self._tile_manager)
            if path:
                cost = path_cost(path, self._tile_manager)
                self.actor.movement_remaining = max(
                    0, getattr(self.actor, "movement_remaining", 0) - cost
                )
        elif hasattr(self.actor, "movement_remaining"):
            # No tile manager — use Chebyshev distance * 5ft per tile
            dx = abs(self.target_position[0] - old_pos[0])
            dy = abs(self.target_position[1] - old_pos[1])
            cost = max(dx, dy) * 5  # 5ft per tile
            self.actor.movement_remaining = max(
                0, getattr(self.actor, "movement_remaining", 0) - cost
            )

        self.execution_log.append(
            f"{actor_name} moves from {old_pos} to {self.target_position}"
        )
        app_logger.info(
            f"[Move] {actor_name}: {old_pos} -> {self.target_position}"
        )

        # Fire ENTER_TILE event for trigger system
        world = getattr(self, "_world", None)
        if world:
            from core.gameCreation.event_bus import EventBus
            from core.events import TRIGGER_ENTER_TILE
            EventBus.emit(TRIGGER_ENTER_TILE, {
                "entity": self.actor,
                "position": self.target_position,
                "old_position": old_pos,
                "world": world,
            })

        return {
            "action": "move",
            "actor": actor_name,
            "from": old_pos,
            "to": self.target_position,
        }

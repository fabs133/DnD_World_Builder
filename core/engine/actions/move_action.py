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

                # Check movement budget (entity.speed in feet)
                speed = getattr(self.actor, "speed", None)
                if speed is not None:
                    cost = path_cost(path, self._tile_manager)
                    if cost > speed:
                        self.execution_log.append(
                            f"Path cost {cost}ft exceeds speed {speed}ft"
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
            self.actor.position = self.target_position

        self.execution_log.append(
            f"{actor_name} moves from {old_pos} to {self.target_position}"
        )
        app_logger.info(
            f"[Move] {actor_name}: {old_pos} -> {self.target_position}"
        )
        return {
            "action": "move",
            "actor": actor_name,
            "from": old_pos,
            "to": self.target_position,
        }

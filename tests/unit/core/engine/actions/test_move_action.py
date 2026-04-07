"""Tests for MoveAction."""

import pytest
from core.engine.actions.move_action import MoveAction
from models.world.world_tile_manager import WorldTileManager


class SimpleEntity:
    def __init__(self, name, hp=10, position=(0, 0), speed=30):
        self.name = name
        self.hp = hp
        self.position = position
        self.speed = speed


class TestMoveAction:
    def test_move_updates_position(self):
        actor = SimpleEntity("Fighter", position=(0, 0))
        action = MoveAction(actor, target_position=(2, 3))
        result = action.execute(None)

        assert actor.position == (2, 3)
        assert result["from"] == (0, 0)
        assert result["to"] == (2, 3)

    def test_move_with_tile_manager(self):
        tm = WorldTileManager(5, 5, "square")
        actor = SimpleEntity("Fighter", position=(0, 0))
        tm.place_entity(actor, 0, 0)

        action = MoveAction(actor, target_position=(1, 1), world_tile_manager=tm)
        result = action.execute(None)

        assert actor.position == (1, 1)

    def test_validate_invalid_tile(self):
        tm = WorldTileManager(5, 5, "square")
        actor = SimpleEntity("Fighter")
        action = MoveAction(actor, target_position=(10, 10), world_tile_manager=tm)

        assert action.validate(None) is False

    def test_validate_valid_tile(self):
        tm = WorldTileManager(5, 5, "square")
        actor = SimpleEntity("Fighter")
        action = MoveAction(actor, target_position=(2, 2), world_tile_manager=tm)

        assert action.validate(None) is True

    def test_validate_dead_actor(self):
        actor = SimpleEntity("Dead", hp=0)
        action = MoveAction(actor, target_position=(1, 1))

        assert action.validate(None) is False

    def test_execution_log(self):
        actor = SimpleEntity("Fighter", position=(0, 0))
        action = MoveAction(actor, target_position=(1, 1))
        action.execute(None)

        assert len(action.execution_log) >= 1
        assert "Fighter" in action.execution_log[0]

    def test_result_structure(self):
        actor = SimpleEntity("Fighter", position=(0, 0))
        action = MoveAction(actor, target_position=(1, 1))
        result = action.execute(None)

        assert result["action"] == "move"
        assert result["from"] == (0, 0)
        assert result["to"] == (1, 1)


class TestMovementBudget:
    def test_validate_uses_movement_remaining(self):
        """Validation checks movement_remaining when available."""
        tm = WorldTileManager(5, 5, "square")
        actor = SimpleEntity("Fighter", position=(0, 0), speed=30)
        actor.movement_remaining = 5  # only 5ft left
        tm.place_entity(actor, 0, 0)

        # Try to move 3 tiles (15ft) — should fail
        action = MoveAction(actor, target_position=(3, 0), world_tile_manager=tm)
        assert action.validate(None) is False

    def test_validate_allows_within_remaining(self):
        """Movement within remaining budget passes validation."""
        tm = WorldTileManager(5, 5, "square")
        actor = SimpleEntity("Fighter", position=(0, 0), speed=30)
        actor.movement_remaining = 15
        tm.place_entity(actor, 0, 0)

        # Move 2 tiles (10ft) — should pass
        action = MoveAction(actor, target_position=(2, 0), world_tile_manager=tm)
        assert action.validate(None) is True

    def test_movement_budget_deducted_after_execute(self):
        """Moving deducts from movement_remaining."""
        tm = WorldTileManager(5, 5, "square")
        actor = SimpleEntity("Fighter", position=(0, 0), speed=30)
        actor.movement_remaining = 30
        tm.place_entity(actor, 0, 0)

        action = MoveAction(actor, target_position=(2, 0), world_tile_manager=tm)
        action.execute(None)

        # 2 tiles * 5ft = 10ft deducted, 20ft remaining
        assert actor.movement_remaining == 20

    def test_fallback_to_speed_without_movement_remaining(self):
        """When movement_remaining is not set, falls back to speed."""
        tm = WorldTileManager(5, 5, "square")
        actor = SimpleEntity("Fighter", position=(0, 0), speed=30)
        # No movement_remaining attribute
        tm.place_entity(actor, 0, 0)

        action = MoveAction(actor, target_position=(4, 0), world_tile_manager=tm)
        assert action.validate(None) is True

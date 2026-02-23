"""Tests for MoveAction."""

import pytest
from core.engine.actions.move_action import MoveAction
from models.world.world_tile_manager import WorldTileManager


class SimpleEntity:
    def __init__(self, name, hp=10, position=(0, 0)):
        self.name = name
        self.hp = hp
        self.position = position


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

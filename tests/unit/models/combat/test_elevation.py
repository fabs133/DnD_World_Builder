"""Tests for elevation data model and traversal evaluation."""

from models.combat.elevation import (
    evaluate_traversal, elevation_blocks_vision,
    TraversalType, STEP_THRESHOLD, CLIMB_THRESHOLD,
)
from models.tiles.tile_data import TileData, TerrainType


class TestEvaluateTraversal:

    def test_flat(self):
        info = evaluate_traversal(0, 0)
        assert info.traversal_type == TraversalType.FLAT
        assert info.movement_cost_multiplier == 1.0

    def test_step_up_one(self):
        info = evaluate_traversal(0, 1)
        assert info.traversal_type == TraversalType.STEP
        assert info.movement_cost_multiplier == 1.0

    def test_step_down_one(self):
        info = evaluate_traversal(1, 0)
        assert info.traversal_type == TraversalType.STEP
        assert info.elevation_diff == -1

    def test_climb_two(self):
        info = evaluate_traversal(0, 2)
        assert info.traversal_type == TraversalType.CLIMB
        assert info.movement_cost_multiplier == 2.0

    def test_climb_three_requires_check(self):
        info = evaluate_traversal(0, 3)
        assert info.traversal_type == TraversalType.CLIMB_HARD
        assert info.requires_check is True
        assert info.check_dc == 15

    def test_impassable_four_up(self):
        info = evaluate_traversal(0, 4)
        assert info.traversal_type == TraversalType.IMPASSABLE

    def test_jump_down_two(self):
        info = evaluate_traversal(2, 0)
        assert info.traversal_type == TraversalType.JUMP_DOWN
        assert info.fall_damage_dice == 1

    def test_jump_down_three(self):
        info = evaluate_traversal(3, 0)
        assert info.fall_damage_dice == 2

    def test_flying_ignores(self):
        info = evaluate_traversal(0, 5, has_fly_speed=True)
        assert info.traversal_type == TraversalType.FLAT

    def test_climb_speed_reduces_cost(self):
        info = evaluate_traversal(0, 2, has_climb_speed=True)
        assert info.movement_cost_multiplier == 1.0  # reduced from 2.0


class TestElevationBlocksVision:

    def test_blocked_by_higher(self):
        assert elevation_blocks_vision(0, 2, 0) is True

    def test_not_blocked_viewer_higher(self):
        assert elevation_blocks_vision(3, 2, 0) is False

    def test_not_blocked_target_higher(self):
        assert elevation_blocks_vision(0, 2, 3) is False

    def test_not_blocked_same(self):
        assert elevation_blocks_vision(1, 1, 1) is False


class TestTileDataElevation:

    def test_default_zero(self):
        td = TileData(position=(0, 0), terrain=TerrainType.FLOOR)
        assert td.elevation == 0

    def test_roundtrip(self):
        td = TileData(position=(0, 0), terrain=TerrainType.FLOOR, elevation=3)
        data = td.to_dict()
        assert data["elevation"] == 3
        restored = TileData.from_dict(data)
        assert restored.elevation == 3

    def test_backward_compat(self):
        data = {
            "tile_id": "old",
            "position": [0, 0],
            "terrain": "FLOOR",
            "tags": [],
            "entities": [],
            "triggers": [],
        }
        td = TileData.from_dict(data)
        assert td.elevation == 0

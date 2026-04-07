"""Tests for combat grid generator."""

from models.combat.grid_generator import generate_combat_grid
from models.combat.encounter_template import TerrainPreset
from models.tiles.tile_data import TileTag


class TestGridGenerator:

    def _preset(self, **overrides):
        defaults = dict(
            preset_id="test", name="Test",
            base_terrain="floor",
            obstacles=[
                {"terrain": "wall", "label": "Rock", "blocks_movement": True,
                 "blocks_vision": False, "size": [1, 1], "weight": 1.0},
            ],
            obstacle_density=0.1,
            difficult_terrain_chance=0.05,
        )
        defaults.update(overrides)
        return TerrainPreset(**defaults)

    def test_dimensions(self):
        grid = generate_combat_grid(8, 6, self._preset(), seed=42)
        assert len(grid) == 48  # 8 * 6

    def test_deterministic_with_seed(self):
        preset = self._preset()
        g1 = generate_combat_grid(10, 10, preset, seed=42)
        g2 = generate_combat_grid(10, 10, preset, seed=42)
        labels1 = {pos: t.user_label for pos, t in g1.items()}
        labels2 = {pos: t.user_label for pos, t in g2.items()}
        assert labels1 == labels2

    def test_obstacles_within_bounds(self):
        grid = generate_combat_grid(10, 10, self._preset(obstacle_density=0.3), seed=42)
        for pos, tile in grid.items():
            assert 0 <= pos[0] < 10
            assert 0 <= pos[1] < 10

    def test_spawn_area_clear(self):
        """Bottom 2 rows should have no obstacles."""
        preset = self._preset(obstacle_density=0.5)
        grid = generate_combat_grid(10, 10, preset, seed=42)
        for x in range(10):
            for y in [8, 9]:  # bottom 2 rows
                tile = grid[(x, y)]
                assert TileTag.BLOCKS_MOVEMENT not in tile.tags

    def test_obstacle_density_approximate(self):
        preset = self._preset(obstacle_density=0.15)
        grid = generate_combat_grid(10, 10, preset, seed=42)
        blocked = sum(
            1 for t in grid.values()
            if TileTag.BLOCKS_MOVEMENT in t.tags
        )
        # 80 eligible cells (10x8, minus spawn rows), ~12 expected
        assert 3 <= blocked <= 25

    def test_difficult_terrain_applied(self):
        preset = self._preset(difficult_terrain_chance=0.3, obstacle_density=0.0)
        grid = generate_combat_grid(10, 10, preset, seed=42)
        difficult = sum(1 for t in grid.values() if t.movement_cost > 5)
        assert difficult > 0

    def test_no_obstacles_when_density_zero(self):
        preset = self._preset(obstacle_density=0.0, difficult_terrain_chance=0.0)
        grid = generate_combat_grid(5, 5, preset, seed=42)
        blocked = sum(1 for t in grid.values() if TileTag.BLOCKS_MOVEMENT in t.tags)
        assert blocked == 0

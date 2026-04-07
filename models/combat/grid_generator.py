"""Combat grid generation from terrain presets.

Pure Python — generates a grid of TileData from a TerrainPreset.
"""

from __future__ import annotations

import random
from typing import Dict, Optional, Tuple

from models.tiles.tile_data import TileData, TerrainType, TileTag
from models.combat.encounter_template import TerrainPreset


def generate_combat_grid(
    width: int,
    height: int,
    preset: TerrainPreset,
    seed: int | None = None,
) -> Dict[Tuple[int, int], TileData]:
    """Generate a combat grid populated with obstacles from a terrain preset.

    Player spawn area (bottom 2 rows) is kept clear of obstacles.

    :param width: Grid columns.
    :param height: Grid rows.
    :param preset: TerrainPreset defining obstacle pool and density.
    :param seed: Random seed for deterministic generation.
    :returns: Dict mapping ``(col, row)`` to TileData.
    """
    rng = random.Random(seed)

    terrain_map = {
        "grass": TerrainType.GRASS,
        "floor": TerrainType.FLOOR,
        "water": TerrainType.WATER,
    }
    base = terrain_map.get(preset.base_terrain, TerrainType.FLOOR)

    # 1. Create base grid
    grid: Dict[Tuple[int, int], TileData] = {}
    for x in range(width):
        for y in range(height):
            grid[(x, y)] = TileData(
                tile_id=f"combat_{x}_{y}",
                position=(x, y),
                terrain=base,
            )

    # 2. Apply difficult terrain
    for x in range(width):
        for y in range(height):
            if y >= height - 2:
                continue  # reserve spawn area
            if rng.random() < preset.difficult_terrain_chance:
                grid[(x, y)].movement_cost = 10  # double cost

    # 3. Place obstacles
    if preset.obstacles:
        total_cells = width * (height - 2)  # exclude spawn rows
        num_obstacles = int(total_cells * preset.obstacle_density)

        # Build weighted obstacle pool
        total_weight = sum(o.get("weight", 1.0) for o in preset.obstacles)
        if total_weight <= 0:
            total_weight = 1.0

        occupied: set[Tuple[int, int]] = set()

        for _ in range(num_obstacles):
            # Pick an obstacle type (weighted)
            roll = rng.random() * total_weight
            chosen = preset.obstacles[0]
            cumulative = 0.0
            for obs in preset.obstacles:
                cumulative += obs.get("weight", 1.0)
                if roll <= cumulative:
                    chosen = obs
                    break

            size = chosen.get("size", [1, 1])
            sx, sy = size[0], size[1]

            # Find a valid position
            for _attempt in range(20):
                px = rng.randint(0, width - sx)
                py = rng.randint(0, height - 2 - sy)  # above spawn area

                cells = [(px + dx, py + dy) for dx in range(sx) for dy in range(sy)]
                if any(c in occupied for c in cells):
                    continue

                # Place the obstacle
                for cx, cy in cells:
                    tile = grid[(cx, cy)]
                    tile.user_label = chosen.get("label", "Obstacle")
                    if chosen.get("blocks_movement", False):
                        if TileTag.BLOCKS_MOVEMENT not in tile.tags:
                            tile.tags.append(TileTag.BLOCKS_MOVEMENT)
                    if chosen.get("blocks_vision", False):
                        if TileTag.BLOCKS_VISION not in tile.tags:
                            tile.tags.append(TileTag.BLOCKS_VISION)
                    # Set elevation from obstacle spec
                    obs_elevation = chosen.get("elevation", 0)
                    if obs_elevation != 0:
                        tile.elevation = obs_elevation
                    occupied.add((cx, cy))
                break

    return grid


def combat_grid_to_tile_dicts(
    grid: Dict[Tuple[int, int], "TileData"],
) -> list[dict]:
    """Convert a combat grid to the tile_dicts format expected by PlayMapScene.

    ``generate_combat_grid`` keys are ``(col, row)`` but PlayMapScene reads
    ``position[0]`` as row and ``position[1]`` as col, so we swap.
    """
    result = []
    for (col, row), td in grid.items():
        d = td.to_dict()
        d["position"] = [row, col]  # PlayMapScene convention: [row, col]
        result.append(d)
    return result

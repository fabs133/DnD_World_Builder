"""Tests for combat grid A* pathfinding and hover integration."""

import pytest
from PyQt5.QtCore import Qt

from ui.combat.play_map_widget import PlayMapScene
from models.entities.game_entity import GameEntity


def make_entity(name, entity_type="player", hp=20, position=(0, 0),
                armor_class=12, speed=30):
    e = GameEntity(name=name, entity_type=entity_type,
                   stats={"hp": hp, "max_hp": hp, "armor_class": armor_class,
                          "speed": speed})
    e.position = position
    e.movement_remaining = speed
    e.action_used = False
    e.bonus_action_used = False
    e.reaction_used = False
    return e


def make_tile_dicts(width=10, height=10, terrain="GRASS", blocked=None):
    blocked = blocked or set()
    tiles = []
    for r in range(height):
        for c in range(width):
            tags = ["BLOCKS_MOVEMENT"] if (r, c) in blocked else []
            tiles.append({
                "tile_id": f"combat_{r}_{c}",
                "position": [r, c],
                "terrain": terrain,
                "tags": tags,
                "elevation": 0,
            })
    return tiles


def _make_scene_with_entities(blocked=None, entities=None, width=10, height=10):
    """Create a PlayMapScene with optional blocked tiles and entities."""
    tile_dicts = make_tile_dicts(width, height, blocked=blocked)
    scene = PlayMapScene(tile_dicts, tile_size=48)
    scene.set_fog_enabled(False)
    if entities:
        scene.update_entities(entities)
    return scene


def _find_path_on_scene(scene, start, goal, current_entity_name="Fighter"):
    """Run the same A* used by PlaySessionDialog._combat_grid_find_path."""
    import heapq

    tiles = scene._tiles
    entity_pos = scene._entity_positions

    if goal not in tiles:
        return None
    td = scene._tile_dict_by_pos.get(goal, {})
    if "BLOCKS_MOVEMENT" in td.get("tags", []):
        return None
    if goal in entity_pos and entity_pos[goal].name != current_entity_name:
        return None

    def blocked(pos):
        if pos not in tiles:
            return True
        td = scene._tile_dict_by_pos.get(pos, {})
        if "BLOCKS_MOVEMENT" in td.get("tags", []):
            return True
        if pos in entity_pos and pos != start:
            return True
        return False

    counter = 0
    open_set = [(0, counter, start)]
    came_from = {}
    g_score = {start: 0}
    while open_set:
        _, _, current = heapq.heappop(open_set)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path
        cr, cc = current
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nb = (cr + dr, cc + dc)
                if blocked(nb):
                    continue
                tentative = g_score[current] + 1
                if tentative < g_score.get(nb, float("inf")):
                    came_from[nb] = current
                    g_score[nb] = tentative
                    h = max(abs(nb[0] - goal[0]), abs(nb[1] - goal[1]))
                    counter += 1
                    heapq.heappush(open_set, (tentative + h, counter, nb))
    return None


# ── A* on combat grid ───────────────────────────────────────────────


class TestCombatGridPathfinding:

    def test_path_to_adjacent_tile(self, qapp):
        scene = _make_scene_with_entities()
        path = _find_path_on_scene(scene, (5, 5), (5, 6))
        assert path == [(5, 5), (5, 6)]

    def test_path_around_obstacle(self, qapp):
        blocked = {(5, 6)}
        scene = _make_scene_with_entities(blocked=blocked)
        path = _find_path_on_scene(scene, (5, 5), (5, 7))
        assert path is not None
        assert len(path) >= 3  # Must go around
        assert (5, 6) not in path  # Must not pass through obstacle

    def test_path_around_entity(self, qapp):
        enemy = make_entity("Wolf", "enemy", hp=11, position=(5, 6))
        scene = _make_scene_with_entities(entities=[enemy])
        path = _find_path_on_scene(scene, (5, 5), (5, 7))
        assert path is not None
        assert (5, 6) not in path  # Must go around occupied tile

    def test_path_to_blocked_tile_returns_none(self, qapp):
        blocked = {(5, 7)}
        scene = _make_scene_with_entities(blocked=blocked)
        path = _find_path_on_scene(scene, (5, 5), (5, 7))
        assert path is None

    def test_path_to_occupied_tile_returns_none(self, qapp):
        enemy = make_entity("Wolf", "enemy", hp=11, position=(5, 7))
        scene = _make_scene_with_entities(entities=[enemy])
        path = _find_path_on_scene(scene, (5, 5), (5, 7))
        assert path is None

    def test_path_off_grid_returns_none(self, qapp):
        scene = _make_scene_with_entities(width=5, height=5)
        path = _find_path_on_scene(scene, (2, 2), (99, 99))
        assert path is None

    def test_path_diagonal_movement(self, qapp):
        scene = _make_scene_with_entities()
        path = _find_path_on_scene(scene, (5, 5), (7, 7))
        assert path is not None
        # Diagonal: should be 2 steps (Chebyshev)
        assert len(path) == 3  # start + 2 diagonal steps

    def test_path_long_route(self, qapp):
        scene = _make_scene_with_entities()
        path = _find_path_on_scene(scene, (0, 0), (9, 9))
        assert path is not None
        # Diagonal distance is max(9,9) = 9 steps + start = 10
        assert len(path) == 10


# ── Hover integration ───────────────────────────────────────────────


class TestHoverIntegration:

    def test_show_path_preview_in_range(self, qapp):
        scene = _make_scene_with_entities()
        path = [(5, 5), (5, 6), (5, 7)]
        scene.show_path_preview(path, in_range=True)
        assert len(scene._path_items) > 0
        # Check color is blue (in-range)
        line = scene._path_items[0]
        pen_color = line.pen().color()
        assert pen_color.name() == "#378add"

    def test_show_path_preview_out_of_range(self, qapp):
        scene = _make_scene_with_entities()
        path = [(5, 5), (5, 6), (5, 7)]
        scene.show_path_preview(path, in_range=False)
        assert len(scene._path_items) > 0
        line = scene._path_items[0]
        pen_color = line.pen().color()
        assert pen_color.name() == "#888780"

    def test_clear_on_new_path(self, qapp):
        scene = _make_scene_with_entities()
        scene.show_path_preview([(5, 5), (5, 6)], True)
        old_items = list(scene._path_items)
        scene.show_path_preview([(3, 3), (3, 4)], True)
        # Old items should be gone
        for item in old_items:
            assert item.scene() is None

    def test_clear_path_preview_idempotent(self, qapp):
        scene = _make_scene_with_entities()
        scene.clear_path_preview()
        scene.clear_path_preview()  # Should not crash

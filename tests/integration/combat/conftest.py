"""Shared fixtures for combat integration tests."""

import pytest
from unittest.mock import MagicMock

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from models.entities.game_entity import GameEntity
from core.gameCreation.event_bus import EventBus


@pytest.fixture(autouse=True)
def reset_bus():
    EventBus.reset()
    yield
    EventBus.reset()


def make_entity(name, entity_type="player", hp=20, position=(0, 0),
                armor_class=12, speed=30):
    """Create a minimal GameEntity for testing."""
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
    """Create a list of tile dicts for PlayMapScene.

    Args:
        blocked: set of (row, col) positions that should block movement.
    """
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


@pytest.fixture
def _make_entity():
    """Fixture wrapper for make_entity helper."""
    return make_entity


@pytest.fixture
def _make_tile_dicts():
    """Fixture wrapper for make_tile_dicts helper."""
    return make_tile_dicts


@pytest.fixture
def tile_dicts_10x10():
    return make_tile_dicts(10, 10)


@pytest.fixture
def three_players():
    return [
        make_entity("Fighter", "player", hp=28, position=(8, 3)),
        make_entity("Rogue", "player", hp=24, position=(9, 4)),
        make_entity("Cleric", "player", hp=22, position=(8, 5)),
    ]


@pytest.fixture
def four_enemies():
    return [
        make_entity("Wolf 1", "enemy", hp=11, position=(1, 3)),
        make_entity("Wolf 2", "enemy", hp=11, position=(1, 5)),
        make_entity("Wolf 3", "enemy", hp=11, position=(2, 4)),
        make_entity("Wolf 4", "enemy", hp=11, position=(0, 4)),
    ]


@pytest.fixture
def combat_entities(three_players, four_enemies):
    return three_players + four_enemies


@pytest.fixture
def combat_scene(tile_dicts_10x10, combat_entities):
    """Create a PlayMapScene with entities placed and updated."""
    from ui.combat.play_map_widget import PlayMapScene
    scene = PlayMapScene(tile_dicts_10x10, tile_size=48)
    scene.set_fog_enabled(False)
    scene.update_entities(combat_entities, current_name="Fighter")
    return scene

import logging
import pytest
from core.logger import app_logger
from models.world.world_tile_manager import WorldTileManager
from models.tiles.tile_data import TileData

class DummyEntity:
    def __init__(self, name):
        self.name = name
        self.position = None

def test_generate_tiles_and_init():
    w, h = 3, 2
    mgr = WorldTileManager(w, h, tile_type="square")
    # tiles dict should have w*h entries
    assert len(mgr.tiles) == w * h
    # keys cover (0..w-1,0..h-1)
    for x in range(w):
        for y in range(h):
            assert (x, y) in mgr.tiles
            td = mgr.tiles[(x, y)]
            assert isinstance(td, TileData)
            assert td.position == (x, y)
    # entities mapping is empty
    assert mgr.entities == {}

def test_is_valid_tile():
    mgr = WorldTileManager(2, 2, tile_type="square")
    assert mgr.is_valid_tile(0, 0)
    assert mgr.is_valid_tile(1, 1)
    assert not mgr.is_valid_tile(-1, 0)
    assert not mgr.is_valid_tile(2, 0)
    assert not mgr.is_valid_tile(0, 2)

@pytest.mark.parametrize("tile_type,expected", [
    ("square", {(1,0),(1,2),(0,1),(2,1)}),
    ("hex",    {(1,0),(1,2),(0,1),(2,1),(0,2),(2,0)}),
])
def test_get_adjacent_tiles(tile_type, expected):
    mgr = WorldTileManager(3, 3, tile_type=tile_type)
    adj = set(mgr.get_adjacent_tiles(1, 1))
    assert adj == expected

def test_place_and_get_entities(caplog):
    mgr = WorldTileManager(2, 2, tile_type="square")
    ent = DummyEntity("Hero")
    # place at valid tile
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        mgr.place_entity(ent, 1, 1)
    assert "Placed Hero at (1, 1)" in caplog.text
    # entity.position updated
    assert ent.position == (1, 1)
    # get_entities_at returns the list
    assert mgr.get_entities_at(1, 1) == [ent]
    # invalid placement raises
    bad = DummyEntity("Orc")
    with pytest.raises(ValueError):
        mgr.place_entity(bad, -1, 0)

def test_move_entity_prints_and_updates_position(caplog):
    mgr = WorldTileManager(2, 2, tile_type="square")
    ent = DummyEntity("Rogue")
    # valid move
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        mgr.move_entity(ent, 0, 1)
    assert ent.position == (0, 1)
    assert "Rogue moved to tile (0, 1)" in caplog.text
    # invalid move
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        mgr.move_entity(ent, 3, 3)
    # position unchanged
    assert ent.position == (0, 1)
    assert "Invalid move for Rogue." in caplog.text

def test_display_world(caplog):
    mgr = WorldTileManager(4, 2, tile_type="square")
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        mgr.display_world()
    # Should contain two lines of "[ ][ ][ ][ ]"
    lines = [line for line in caplog.text.splitlines() if "[ ]" in line]
    assert len(lines) == 2
    for line in lines:
        assert "[ ][ ][ ][ ]" in line

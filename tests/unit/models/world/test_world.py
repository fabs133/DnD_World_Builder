import sqlite3
import pytest

from models.world.world import World
from models.world.world_tile_manager import WorldTileManager
from models.tiles.tile_data import TileTag
from models.world.world_lore import WorldLore
from core.gameCreation.turn_manager import TurnManager

class DummyEntity:
    def __init__(self, name):
        self.name = name
        self.position = None

@pytest.fixture
def world_empty(monkeypatch):
    # Create a World but stub out TurnManager so we don't need its real constructor
    monkeypatch.setattr(TurnManager, "__init__", lambda self: None)
    world = World(
        world_version=1,
        width=3,
        height=3,
        tile_type="square",
        description="Desc",
        map_data={},
        time_of_day="noon",
        weather_conditions="clear"
    )
    return world

def test_initialization(world_empty):
    w = world_empty
    # tile_manager is a WorldTileManager
    assert isinstance(w.tile_manager, WorldTileManager)
    assert w.world_version == 1
    # lore is a WorldLore
    assert isinstance(w.lore, WorldLore)
    # turn_manager is a TurnManager
    assert isinstance(w.turn_manager, TurnManager)

def test_place_and_get_entities_delegation(world_empty):
    w = world_empty
    ent = DummyEntity("Hero")
    # Place via World
    w.place_entity(ent, 1, 2)
    # Should appear in tile_manager and via get_entities_at
    assert ent in w.tile_manager.entities[(1, 2)]
    assert w.get_entities_at(1, 2) == [ent]

def test_move_and_get_adjacent_delegation(world_empty):
    w = world_empty
    ent = DummyEntity("Rogue")
    # First place
    w.place_entity(ent, 0, 0)
    # Move via World
    w.move_entity(ent, 2, 2)
    assert ent.position == (2, 2)
    # Test adjacency uses WorldTileManager logic
    adj = w.get_adjacent_tiles(1, 1)
    # For a 3×3 square grid at (1,1), should be the four orthogonals
    assert set(adj) == {(1,0), (1,2), (0,1), (2,1)}

def test_describe_update_and_save_delegation(world_empty):
    w = world_empty
    # stub out lore
    class StubLore:
        def __init__(self):
            self.last_weather = None
            self.last_time = None
            self.saved_db = None
        def describe_world(self):
            return "WORLD!"
        def update_weather(self, nw):
            self.last_weather = nw
        def update_time_of_day(self, nt):
            self.last_time = nt
        def save_to_db(self, db_conn):
            self.saved_db = db_conn

    stub = StubLore()
    w.lore = stub

    assert w.describe_world() == "WORLD!"
    w.update_weather("rainy")
    assert stub.last_weather == "rainy"
    w.update_time_of_day("dusk")
    assert stub.last_time == "dusk"

    # Test save_to_db delegation
    conn = sqlite3.connect(":memory:")
    w.save_to_db(conn)
    assert stub.saved_db is conn

@pytest.mark.parametrize("from_pos,to_pos,max_range,expected", [
    ((0,0),(0,0),0, True),    # same tile
    ((0,0),(0,1),1, True),    # adjacent within range
    ((0,0),(0,2),1, False),   # out of manhattan range
    ((1,1),(2,2),2, True),    # diagonal within range, no intermediate
])
def test_can_see_simple(world_empty, from_pos, to_pos, max_range, expected):
    w = world_empty
    assert w.can_see(from_pos, to_pos, max_range) is expected

def test_can_see_blocked_by_vision_tag(world_empty):
    w = world_empty
    # from (0,0) to (0,2) with max_range=2 → intermediate (0,1)
    # Tag that tile as blocking vision
    w.tile_manager.tiles[(0,1)].tags.append(TileTag.BLOCKS_VISION)
    assert w.can_see((0,0), (0,2), 2) is False

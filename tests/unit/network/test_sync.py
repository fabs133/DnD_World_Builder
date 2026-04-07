import pytest
from network.sync import serialize_world, serialize_entity, compute_delta, apply_delta
from models.world.world import World
from models.entities.game_entity import GameEntity


@pytest.fixture
def simple_world():
    """A minimal 2x2 world with one entity."""
    world = World(
        world_version=1, width=2, height=2,
        tile_type="square", description="Test",
        map_data={}, time_of_day="day", weather_conditions="clear"
    )
    entity = GameEntity("Hero", "player", stats={"hp": 20})
    world.place_entity(entity, 0, 0)
    return world


class TestSerializeWorld:

    def test_contains_expected_top_level_keys(self, simple_world):
        data = serialize_world(simple_world)
        assert data["width"] == 2
        assert data["height"] == 2
        assert data["tile_type"] == "square"
        assert "tiles" in data
        assert "entities" in data
        assert "lore" in data
        assert "turn" in data

    def test_tiles_keyed_by_position(self, simple_world):
        data = serialize_world(simple_world)
        assert "0,0" in data["tiles"]
        assert "1,1" in data["tiles"]
        assert len(data["tiles"]) == 4  # 2x2 grid

    def test_entities_serialized(self, simple_world):
        data = serialize_world(simple_world)
        assert "0,0" in data["entities"]
        assert len(data["entities"]["0,0"]) == 1
        assert data["entities"]["0,0"][0]["name"] == "Hero"

    def test_lore_serialized(self, simple_world):
        data = serialize_world(simple_world)
        assert data["lore"]["description"] == "Test"
        assert data["lore"]["time_of_day"] == "day"
        assert data["lore"]["weather_conditions"] == "clear"

    def test_turn_serialized(self, simple_world):
        data = serialize_world(simple_world)
        assert "current_turn" in data["turn"]
        assert data["turn"]["current_turn"] == 0


class TestSerializeEntity:

    def test_basic_entity(self):
        e = GameEntity("Goblin", "enemy", stats={"hp": 5})
        e.position = (1, 2)
        data = serialize_entity(e)
        assert data["name"] == "Goblin"
        assert data["entity_type"] == "enemy"
        assert data["stats"]["hp"] == 5
        assert data["position"] == [1, 2]

    def test_entity_without_position(self):
        e = GameEntity("NPC", "npc")
        data = serialize_entity(e)
        assert data["name"] == "NPC"
        assert "position" not in data

    def test_entity_with_none_position(self):
        e = GameEntity("NPC", "npc")
        e.position = None
        data = serialize_entity(e)
        assert "position" not in data


class TestComputeDelta:

    def test_no_changes(self):
        state = {"tiles": {"0,0": {"terrain": "FLOOR"}}, "entities": {}, "lore": {}, "turn": {}}
        assert compute_delta(state, state) == []

    def test_tile_update(self):
        old = {"tiles": {"0,0": {"terrain": "FLOOR"}}, "entities": {}, "lore": {}, "turn": {}}
        new = {"tiles": {"0,0": {"terrain": "WATER"}}, "entities": {}, "lore": {}, "turn": {}}
        changes = compute_delta(old, new)
        assert len(changes) == 1
        assert changes[0]["op"] == "update"
        assert changes[0]["path"] == "tiles/0,0"
        assert changes[0]["value"] == {"terrain": "WATER"}

    def test_tile_added(self):
        old = {"tiles": {}, "entities": {}, "lore": {}, "turn": {}}
        new = {"tiles": {"1,1": {"terrain": "GRASS"}}, "entities": {}, "lore": {}, "turn": {}}
        changes = compute_delta(old, new)
        assert any(c["op"] == "add" and c["path"] == "tiles/1,1" for c in changes)

    def test_tile_removed(self):
        old = {"tiles": {"0,0": {"terrain": "FLOOR"}}, "entities": {}, "lore": {}, "turn": {}}
        new = {"tiles": {}, "entities": {}, "lore": {}, "turn": {}}
        changes = compute_delta(old, new)
        assert any(c["op"] == "remove" and c["path"] == "tiles/0,0" for c in changes)

    def test_entity_added(self):
        old = {"tiles": {}, "entities": {}, "lore": {}, "turn": {}}
        new = {"tiles": {}, "entities": {"1,1": [{"name": "Orc"}]}, "lore": {}, "turn": {}}
        changes = compute_delta(old, new)
        assert any(c["op"] == "add" and "entities/1,1" == c["path"] for c in changes)

    def test_lore_change(self):
        old = {"tiles": {}, "entities": {}, "lore": {"time": "day"}, "turn": {}}
        new = {"tiles": {}, "entities": {}, "lore": {"time": "night"}, "turn": {}}
        changes = compute_delta(old, new)
        assert any(c["path"] == "lore" for c in changes)

    def test_turn_change(self):
        old = {"tiles": {}, "entities": {}, "lore": {}, "turn": {"current_turn": 0}}
        new = {"tiles": {}, "entities": {}, "lore": {}, "turn": {"current_turn": 1}}
        changes = compute_delta(old, new)
        assert any(c["path"] == "turn" for c in changes)


class TestApplyDelta:

    def test_update_tile(self):
        state = {"tiles": {"0,0": {"terrain": "FLOOR"}}, "entities": {}}
        changes = [{"op": "update", "path": "tiles/0,0", "value": {"terrain": "WATER"}}]
        result = apply_delta(state, changes)
        assert result["tiles"]["0,0"]["terrain"] == "WATER"

    def test_add_entity(self):
        state = {"tiles": {}, "entities": {}}
        changes = [{"op": "add", "path": "entities/1,1", "value": [{"name": "Orc"}]}]
        result = apply_delta(state, changes)
        assert result["entities"]["1,1"] == [{"name": "Orc"}]

    def test_remove_entity(self):
        state = {"tiles": {}, "entities": {"1,1": [{"name": "Orc"}]}}
        changes = [{"op": "remove", "path": "entities/1,1"}]
        result = apply_delta(state, changes)
        assert "1,1" not in result["entities"]

    def test_update_top_level_key(self):
        state = {"tiles": {}, "lore": {"time": "day"}}
        changes = [{"op": "update", "path": "lore", "value": {"time": "night"}}]
        result = apply_delta(state, changes)
        assert result["lore"] == {"time": "night"}

    def test_does_not_mutate_input(self):
        state = {"tiles": {"0,0": {"terrain": "FLOOR"}}, "entities": {}}
        changes = [{"op": "update", "path": "tiles/0,0", "value": {"terrain": "WATER"}}]
        apply_delta(state, changes)
        assert state["tiles"]["0,0"]["terrain"] == "FLOOR"

    def test_roundtrip_with_compute_delta(self):
        """compute_delta then apply_delta should produce the new state."""
        old = {
            "tiles": {"0,0": {"t": "FLOOR"}, "0,1": {"t": "GRASS"}},
            "entities": {"0,0": [{"n": "Hero"}]},
            "lore": {"d": "A"},
            "turn": {"ct": 0},
        }
        new = {
            "tiles": {"0,0": {"t": "WATER"}, "0,1": {"t": "GRASS"}},
            "entities": {"0,0": [{"n": "Hero"}], "1,0": [{"n": "Goblin"}]},
            "lore": {"d": "B"},
            "turn": {"ct": 1},
        }
        delta = compute_delta(old, new)
        result = apply_delta(old, delta)
        assert result == new

    def test_empty_changes(self):
        state = {"tiles": {"0,0": {"terrain": "FLOOR"}}}
        result = apply_delta(state, [])
        assert result == state

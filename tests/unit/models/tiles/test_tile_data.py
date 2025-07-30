import pytest

import models.tiles.tile_data as td_mod
from models.tiles.tile_data import (
    TileData, TerrainType, TileTag
)
from core.gameCreation.trigger import Trigger
from core.gameCreation.event_bus import EventBus

# A dummy GameEntity for testing occupancy, to_dict/from_dict
class DummyEntity:
    def __init__(self, name, etype):
        self.name = name
        self.entity_type = etype
        self.to_dict_called = False

    def to_dict(self):
        self.to_dict_called = True
        return {"name": self.name, "type": self.entity_type}

# A dummy Trigger for testing register, to_dict/from_dict
class DummyTrigger:
    def __init__(self, event_type="evt"):
        self.event_type = event_type
        self.check_and_react = lambda data: None
        self.to_dict_called = False

    def to_dict(self):
        self.to_dict_called = True
        return {"type": "Dummy", "event": self.event_type}

    @classmethod
    def from_dict(cls, data):
        return DummyTrigger(event_type=data["event"])

@pytest.fixture(autouse=True)
def clear_eventbus(monkeypatch):
    # Capture subscriptions
    subs = []
    monkeypatch.setattr(EventBus, "subscribe",
                        classmethod(lambda cls, et, cb: subs.append((et, cb))))
    return subs

def test_terrain_and_tag_enums():
    assert TerrainType.WATER.value == "water"
    assert TerrainType.CUSTOM.name == "CUSTOM"
    assert TileTag.START_ZONE.value == "start_zone"
    assert TileTag.BLOCKS_VISION.name == "BLOCKS_VISION"

def test_is_occupied_and_has_entity_type():
    # No entities
    td = TileData()
    assert td.is_occupied() is False
    assert td.has_entity_type("player") is False

    # Non‐occupying entity
    non = DummyEntity("X", "object")
    td.add_entity(non)
    assert td.is_occupied() is False

    # Occupying entity
    player = DummyEntity("Hero", "player")
    td.add_entity(player)
    assert td.is_occupied() is True
    assert td.has_entity_type("player") is True
    assert td.has_entity_type("enemy") is False

def test_add_and_remove_entity():
    td = TileData()
    e = DummyEntity("E", "npc")
    td.add_entity(e)
    assert e in td.entities

    td.remove_entity(e)
    assert e not in td.entities

    # Removing again is no‐op
    td.remove_entity(e)
    assert e not in td.entities

def test_register_trigger(monkeypatch, clear_eventbus):
    td = TileData()
    trig = DummyTrigger(event_type="EVT")
    td.register_trigger(trig)

    # Should append
    assert trig in td.triggers
    # Should subscribe exactly once
    assert clear_eventbus == [("EVT", trig.check_and_react)]

    # Re-register same trigger: no duplicate and no extra subscribe
    td.register_trigger(trig)
    assert td.triggers.count(trig) == 1
    assert len(clear_eventbus) == 1

def test_to_dict_includes_all_fields():
    trig = DummyTrigger(event_type="TIN")
    ent = DummyEntity("N", "npc")

    td = TileData(
        tile_id="T1",
        position=(3,4),
        terrain=TerrainType.MOUNTAIN,
        entities=[ent],
        note="A note",
        user_label="Label",
        overlay_color="#AAAAAA",
        tags=[TileTag.BLOCKS_MOVEMENT, TileTag.TRAP_ZONE],
        last_updated="2025-05-15T12:00:00",
        triggers=[trig]
    )

    out = td.to_dict()
    # Basic fields
    assert out["tile_id"] == "T1"
    assert out["position"] == (3,4)
    assert out["terrain"] == "MOUNTAIN"
    # Enums -> names
    assert out["tags"] == ["BLOCKS_MOVEMENT", "TRAP_ZONE"]
    # Optional strings
    assert out["note"] == "A note"
    assert out["user_label"] == "Label"
    assert out["overlay_color"] == "#AAAAAA"
    assert out["last_updated"] == "2025-05-15T12:00:00"
    # triggers and entities use to_dict()
    assert out["triggers"] == [{"type":"Dummy", "event":"TIN"}]
    assert trig.to_dict_called is True
    assert out["entities"] == [{"name":"N", "type":"npc"}]
    assert ent.to_dict_called is True

def test_from_dict_roundtrip(monkeypatch, clear_eventbus):
    # Prepare a dict as from JSON
    data = {
        "tile_id": "X1",
        "position": [1,2],
        "terrain": "WATER",
        "tags": ["BLOCKS_MOVEMENT"],   # must match a TileTag member
        "user_label": "U",
        "note": "Note",
        "overlay_color": "#1234FF",
        "last_updated": "2025-01-01T00:00:00",
        "triggers": [{"type":"Dummy","event":"E1"}],
        "entities": [
            {"name":"Ent1","entity_type":"enemy","stats":{},"inventory":[],"triggers":[]}
        ]
    }

    # Stub Trigger.from_dict to our DummyTrigger
    monkeypatch.setattr(Trigger, "from_dict",
                        staticmethod(lambda d: DummyTrigger(event_type=d["event"])))
    # Stub GameEntity.from_dict to return DummyEntity
    monkeypatch.setattr(td_mod.GameEntity, "from_dict",
                        staticmethod(lambda d: DummyEntity(d["name"], d["entity_type"])))

    td = TileData.from_dict(data)
    # Enums restored
    assert isinstance(td.terrain, TerrainType)
    assert td.terrain == TerrainType.WATER
    assert td.tags == [TileTag.BLOCKS_MOVEMENT]
    # Position converted to tuple
    assert td.position == (1,2)
    # Other fields
    assert td.tile_id == "X1"
    assert td.user_label == "U"
    assert td.overlay_color == "#1234FF"
    # Triggers list contains DummyTrigger
    assert len(td.triggers) == 1
    assert isinstance(td.triggers[0], DummyTrigger)
    # Subscription happened once
    assert clear_eventbus == [("E1", td.triggers[0].check_and_react)]
    # Entities list contains DummyEntity
    assert len(td.entities) == 1
    ent = td.entities[0]
    assert isinstance(ent, DummyEntity)
    assert ent.entity_type == "enemy"

import pytest
from core.gameCreation.event_bus import EventBus
from models.game_master import Gamemaster

class DummyEntity:
    def __init__(self, name):
        self.name = name
        self.stats = {"hp": 10}

class DummyScene:
    def __init__(self):
        self.called = False
    def __call__(self, data):
        self.called = True

@pytest.fixture(autouse=True)
def clear_subscriptions(monkeypatch):
    subs = []
    monkeypatch.setattr(EventBus, "subscribe",
                        classmethod(lambda cls, et, cb: subs.append((et, cb))))
    return subs

def test_add_entity_and_stat_blocks():
    gm = Gamemaster()
    e = DummyEntity("Hero")
    gm.add_entity(e)
    assert e in gm.game_entities
    assert gm.stat_blocks["Hero"] == e.stats

def test_encounter_and_event_prints(capsys):
    gm = Gamemaster()

    e = DummyEntity("Orc")
    gm.encounter(e)
    out1 = capsys.readouterr().out.strip()
    assert out1 == "Encounter with Orc!"

    gm.event("A surprise")
    out2 = capsys.readouterr().out.strip()
    assert out2 == "Event: A surprise"

def test_add_item_and_obstacle():
    gm = Gamemaster()
    gm.add_item("Sword")
    gm.add_item("Shield")
    assert gm.world_items == ["Sword", "Shield"]

    gm.add_obstacle("Rock")
    assert gm.temp_obstacles == ["Rock"]

def test_loop_back_prints(capsys):
    gm = Gamemaster()
    gm.loop_back()
    out = capsys.readouterr().out.strip()
    assert "Oh, you thought you could get away" in out

def test_register_scene_trigger_subscribes(clear_subscriptions):
    gm = Gamemaster()
    scene = DummyScene()
    # condition that returns True
    cond = lambda d: True
    gm.register_scene_trigger("EVENT_X", cond, scene)

    # subscription happened
    assert clear_subscriptions == [("EVENT_X", pytest.raises)] or len(clear_subscriptions) == 1
    # simulate an EventBus.emit to invoke the callback
    # find the subscriber:
    event_type, callback = clear_subscriptions[0]
    # call it with data; since cond returns True, scene should be called
    callback({"any": "data"})
    assert scene.called

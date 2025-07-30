import pytest

import models.entities.game_entity as ge_mod
from models.entities.game_entity import GameEntity

# Dummy trigger to exercise to_dict and check_and_react
class DummyTrigger:
    def __init__(self, event_type, label):
        self.event_type = event_type
        self.label = label
        self.to_dict_called = False
        self.checked = []

    def to_dict(self):
        self.to_dict_called = True
        return {"event_type": self.event_type, "label": self.label}

    def check_and_react(self, data):
        self.checked.append(data)


def test_constructor_defaults():
    ge = GameEntity("E1", "player")
    assert ge.name == "E1"
    assert ge.entity_type == "player"
    assert ge.stats == {}
    assert ge.inventory == []
    assert ge.triggers == []
    assert ge.vision_range is None

def test_register_trigger(monkeypatch):
    ge = GameEntity("Hero", "player")
    trig = DummyTrigger("attack", "atk")

    calls = {}
    # stub registry to report “not registered” initially
    monkeypatch.setattr(ge_mod.global_trigger_registry, "is_registered", lambda t: False)
    monkeypatch.setattr(ge_mod.global_trigger_registry, "add_trigger",
                        lambda t, source: calls.setdefault("added", (t, source)))
    monkeypatch.setattr(ge_mod.EventBus, "subscribe",
                        classmethod(lambda cls, et, cb: calls.setdefault("subscribed", (et, cb))))
    # capture info‐logs
    monkeypatch.setattr(ge_mod, "app_logger",
                        type("L",(object,),{"info": lambda *args, **kw: calls.setdefault("info", args)}))

    ge.register_trigger(trig)

    # registration side‐effects
    assert calls["added"] == (trig, "Hero")
    assert calls["subscribed"][0] == "attack"
    assert "info" in calls
    assert trig in ge.triggers

def test_register_trigger_already_registered(monkeypatch):
    ge = GameEntity("Hero", "player")
    trig = DummyTrigger("move", "mv")

    logs = []
    monkeypatch.setattr(ge_mod.global_trigger_registry, "is_registered", lambda t: True)
    # capture debug log when already registered
    monkeypatch.setattr(ge_mod, "app_logger",
                        type("L",(object,),{"debug": lambda *args, **kw: logs.append(args)}))

    ge.register_trigger(trig)
    assert logs, "Expected a debug log when trigger was already registered"
    assert trig in ge.triggers

    # second registration shouldn’t duplicate
    ge.register_trigger(trig)
    assert ge.triggers.count(trig) == 1

def test_to_dict_and_handle_event():
    ge = GameEntity("Gob", "enemy", stats={"hp":5}, inventory=["axe"])
    t1 = DummyTrigger("a", "t1")
    t2 = DummyTrigger("b", "t2")
    ge.triggers = [t1, t2]

    dd = ge.to_dict()
    assert dd["name"] == "Gob"
    assert dd["entity_type"] == "enemy"
    assert dd["stats"] == {"hp":5}
    assert dd["inventory"] == ["axe"]
    # to_dict on triggers should have been called
    assert t1.to_dict_called and t2.to_dict_called
    assert dd["triggers"] == [
        {"event_type":"a","label":"t1"},
        {"event_type":"b","label":"t2"}
    ]

    # only matching event_type fires its trigger
    ge.handle_event("b", {"x":1})
    assert t1.checked == []
    assert t2.checked == [{"x":1}]

def test_from_dict(monkeypatch):
    data = {
        "name": "Z",
        "entity_type": "npc",
        "stats": {"str":2},
        "inventory": ["book"],
        "triggers": [{"event_type":"ev","label":"lbl"}]
    }

    # stub Trigger.from_dict to produce our DummyTrigger
    Monkey = DummyTrigger
    monkeypatch.setattr(ge_mod.Trigger, "from_dict",
                        staticmethod(lambda d: Monkey(d["event_type"], d["label"])))

    registered = []
    # intercept register_trigger so we can see it's called with our DummyTrigger
    monkeypatch.setattr(GameEntity, "register_trigger",
                        lambda self, t: registered.append(t))

    ge = GameEntity.from_dict(data)
    assert ge.name == "Z"
    assert ge.entity_type == "npc"
    assert ge.stats == {"str":2}
    assert ge.inventory == ["book"]

    # ensure we got exactly one trigger, of correct type
    assert len(registered) == 1
    trig = registered[0]
    assert isinstance(trig, DummyTrigger)
    assert trig.event_type == "ev"
    assert trig.label == "lbl"

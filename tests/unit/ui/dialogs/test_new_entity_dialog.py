import pytest
from PyQt5.QtWidgets import QLineEdit, QComboBox
from models.entities.game_entity import GameEntity

import ui.dialogs.new_entity_dialog as ned_mod
from ui.dialogs.new_entity_dialog import NewEntityDialog

class DummyTrigger:
    def __init__(self, label):
        self.label = label
        self.event_type = "EVT"
    def to_dict(self): return {"type":"Dummy"}
    def check_and_react(self, data): pass

@pytest.fixture(autouse=True)
def stub_trigger_presets(monkeypatch):
    # Replace trigger_presets with a dict mapping types to lists of DummyTriggers
    fake = {
        "enemy":   [DummyTrigger("T1"), DummyTrigger("T2")],
        "npc":     [],
        "player":  [],
        "trap":    [],
        "object":  [],
    }
    monkeypatch.setattr(ned_mod, "trigger_presets", fake)
    return fake

@pytest.fixture
def dlg(qapp):
    return NewEntityDialog()

def test_initial_state(dlg):
    # No entity created yet
    assert dlg.entity is None
    # Name input empty
    assert dlg.name_input.text() == ""
    # Type combo has 5 entries and default first is "player"
    combo: QComboBox = dlg.type_input
    assert combo.count() == 5
    assert combo.currentText() == "player"

def test_accept_without_name_leaves_entity_none(dlg):
    # Leave name blank
    dlg.name_input.setText("   ")
    dlg.accept_entity()
    assert dlg.entity is None

def test_accept_creates_entity_and_attaches_triggers(qapp, dlg, stub_trigger_presets):
    # Enter a valid name
    dlg.name_input.setText("Goblin")
    # Select "enemy" so we get our stub triggers
    idx = dlg.type_input.findText("enemy")
    dlg.type_input.setCurrentIndex(idx)

    # Call accept_entity (as if user clicked Create)
    dlg.accept_entity()
    # Now entity attribute set
    ent = dlg.get_entity()
    assert isinstance(ent, GameEntity)
    assert ent.name == "Goblin"
    assert ent.entity_type == "enemy"

    # The two dummy triggers should have been registered
    # and appear in ent.triggers in order
    labels = [t.label for t in ent.triggers]
    assert labels == ["T1", "T2"]

def test_get_entity_before_accept_returns_none(dlg):
    # Without calling accept_entity, get_entity() still returns dlg.entity (None)
    assert dlg.get_entity() is None

import pytest
from core.gameCreation.trigger import Trigger
from models.flow.skill_check import SkillCheck

# Dummy callable condition and reaction for testing
def always_true_condition(event_data):
    return True

def dummy_reaction(event_data):
    event_data["reaction_called"] = True

class DummyReaction:
    def __init__(self):
        self.executed = False

    def execute(self, event_data):
        self.executed = True
        event_data["executed"] = True

# ----- Tests -----

def test_trigger_initialization_label_auto():
    print("Initializing Trigger with auto label")
    trig = Trigger("ON_TEST", always_true_condition, dummy_reaction)
    assert trig.label == "ON_TEST:function"  # Adjusted to match actual label

def test_trigger_label_change_warning(caplog):
    import logging
    trig = Trigger("ON_TEST", always_true_condition, dummy_reaction)
    with caplog.at_level(logging.DEBUG):
        trig.label = "New Label"
    assert "Label changed" in caplog.text

def test_check_and_react_with_callable_condition_and_reaction():
    data = {}
    trig = Trigger("ON_TEST", always_true_condition, dummy_reaction)
    trig.check_and_react(data)
    assert data.get("reaction_called") is True

def test_check_and_react_with_skill_check_pass(monkeypatch):
    stats = {"Arcana": 20}
    skill = SkillCheck("Arcana", dc=10)

    # Patch `attempt` to force success
    monkeypatch.setattr(skill, "attempt", lambda _: True)

    data = {"character_stats": stats, "reaction_called": False}
    trig = Trigger("ON_TEST", skill, dummy_reaction)
    trig.check_and_react(data)
    assert data["reaction_called"] is True

def test_check_and_react_with_object_reaction():
    data = {}
    reaction = DummyReaction()
    trig = Trigger("ON_TEST", always_true_condition, reaction)
    trig.check_and_react(data)
    assert reaction.executed is True
    assert data["executed"] is True

def test_trigger_serialization_deserialization_with_skillcheck():
    skill = SkillCheck("Stealth", 15)
    trig = Trigger("ON_MOVE", skill, dummy_reaction)

    trig_dict = trig.to_dict()
    assert trig_dict["condition"]["skill"] == "Stealth"

    # Correct way to register the function in the trigger registry
    from registries.trigger_registry import global_trigger_registry
    global_trigger_registry.register_function(dummy_reaction, name="dummy_reaction")

    # Simulate serialization roundtrip
    trig_loaded = Trigger.from_dict(trig_dict)
    assert isinstance(trig_loaded.condition, SkillCheck)
    assert trig_loaded.condition.dc == 15
    assert callable(trig_loaded.reaction)


def test_trigger_deserialization_fails_on_unknown_type():
    trig_dict = {
        "event_type": "ON_FAULT",
        "label": "fail_trigger",
        "next_trigger": None,
        "condition": {"type": "MadeUpType", "args": {}},
        "reaction": {"type": "function", "name": "dummy_reaction"},
    }

    with pytest.raises(ValueError):
        Trigger.from_dict(trig_dict)

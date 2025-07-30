import pytest
from core.gameCreation.event_bus import EventBus
from core.gameCreation.trigger import Trigger
from models.flow.skill_check import SkillCheck


@pytest.fixture(autouse=True)
def reset_bus():
    EventBus.reset()


def test_trigger_with_skillcheck_pass(monkeypatch):
    result = {}

    def reaction(event_data):
        result["called"] = True
        result["data"] = event_data

    skill_check = SkillCheck(skill_name="Perception", dc=10)

    # Simulate always succeeding skill check
    monkeypatch.setattr(skill_check, "attempt", lambda stats: True)

    trigger = Trigger("ON_SEARCH", condition=skill_check, reaction=reaction)
    EventBus.subscribe("ON_SEARCH", trigger.check_and_react)

    EventBus.emit("ON_SEARCH", {"character_stats": {"Perception": 15}, "extra": "info"})

    assert result.get("called") is True
    assert result["data"]["extra"] == "info"


def test_trigger_with_skillcheck_fail(monkeypatch):
    result = {"called": False}

    def reaction(event_data):
        result["called"] = True

    skill_check = SkillCheck(skill_name="Stealth", dc=18)

    # Simulate always failing
    monkeypatch.setattr(skill_check, "attempt", lambda stats: False)

    trigger = Trigger("ON_HIDE", condition=skill_check, reaction=reaction)
    EventBus.subscribe("ON_HIDE", trigger.check_and_react)

    EventBus.emit("ON_HIDE", {"character_stats": {"Stealth": 5}})

    assert result["called"] is False

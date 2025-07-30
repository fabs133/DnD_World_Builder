import pytest
from core.gameCreation.event_bus import EventBus
from core.gameCreation.trigger import Trigger
from models.flow.reaction.reactions_list import ApplyDamage
from models.flow.skill_check import SkillCheck
from models.entities.game_entity import GameEntity


class CombatEntity(GameEntity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.damage_log = []

    def take_damage(self, amount, damage_type):
        self.damage_log.append((damage_type, amount))


@pytest.fixture(autouse=True)
def reset_eventbus():
    EventBus.reset()


def test_skillcheck_pass_prevents_damage(monkeypatch):
    rogue = CombatEntity(name="Rogue", entity_type="player")
    guard = CombatEntity(name="Guard", entity_type="npc")
    monkeypatch.setattr("models.flow.skill_check.SkillCheck.attempt", lambda self, stats, *_: True)
    skill = SkillCheck(skill_name="Stealth", dc=10)

    # Always succeed
    


    trigger = Trigger(
        event_type="ON_STEALTH_ATTEMPT",
        condition=skill,
        reaction=ApplyDamage("psychic", 3)
    )

    guard.register_trigger(trigger)

    EventBus.emit("ON_STEALTH_ATTEMPT", {"character_stats": {"Stealth": 20}, "target": rogue})

    assert rogue.damage_log == []


def test_skillcheck_fail_triggers_damage(monkeypatch):
    rogue = CombatEntity(name="Rogue", entity_type="player")
    guard = CombatEntity(name="Guard", entity_type="npc")
    monkeypatch.setattr("models.flow.skill_check.SkillCheck.attempt", lambda self, stats, *_: False)
    skill = SkillCheck(skill_name="Stealth", dc=15)

    # Always fail
    



    trigger = Trigger(
        event_type="ON_STEALTH_ATTEMPT",
        condition=skill,
        reaction=ApplyDamage("psychic", 3)
    )

    guard.register_trigger(trigger)

    EventBus.emit("ON_STEALTH_ATTEMPT", {"character_stats": {"Stealth": 10}, "target": rogue})

    assert ("psychic", 3) in rogue.damage_log

import pytest
from models.entities.game_entity import GameEntity
from models.flow.reaction.reactions_list import ApplyDamage
from models.flow.condition.condition_list import PerceptionCheck
from core.gameCreation.trigger import Trigger
from core.gameCreation.event_bus import EventBus


class DummyEntity(GameEntity):
    def __init__(self, name):
        super().__init__(name=name, entity_type="npc")
        self.damage_log = []

    def take_damage(self, amount, damage_type):
        self.damage_log.append((damage_type, amount))


@pytest.fixture(autouse=True)
def reset_bus():
    EventBus.reset()


def test_trigger_chain_condition_passes():
    target = DummyEntity("Scout")

    reaction = ApplyDamage("psychic", 6)
    chain_trigger = Trigger(
        event_type="CHAINED_EVENT",
        condition=lambda _: True,
        reaction=reaction
    )

    first_trigger = Trigger(
        event_type="SENSOR_CHECK",
        condition=PerceptionCheck(dc=12),
        reaction=lambda _: print("[OK] Initial perception passed."),
        next_trigger=chain_trigger
    )

    target.register_trigger(first_trigger)

    EventBus.emit("SENSOR_CHECK", {"perception": 15, "target": target})

    assert ("psychic", 6) in target.damage_log


def test_trigger_chain_condition_fails():
    target = DummyEntity("Scout")

    reaction = ApplyDamage("psychic", 6)
    chain_trigger = Trigger(
        event_type="CHAINED_EVENT",
        condition=lambda _: True,
        reaction=reaction
    )

    first_trigger = Trigger(
        event_type="SENSOR_CHECK",
        condition=PerceptionCheck(dc=18),
        reaction=lambda _: print("[FAIL] Should not see this."),
        next_trigger=chain_trigger
    )

    target.register_trigger(first_trigger)

    EventBus.emit("SENSOR_CHECK", {"perception": 10, "target": target})

    assert target.damage_log == []

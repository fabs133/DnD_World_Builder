import pytest
from core.gameCreation.trigger import Trigger
from models.flow.condition.condition_list import PerceptionCheck, AlwaysTrue
from models.flow.reaction.reactions_list import ApplyDamage, AlertGamemaster


class DummyTarget:
    def __init__(self):
        self.damage_log = []

    def take_damage(self, amount, damage_type):
        self.damage_log.append((damage_type, amount))


def test_trigger_chain_serialization_roundtrip():
    first_trigger = Trigger(
        event_type="ON_LOOK",
        condition=PerceptionCheck(dc=10),
        reaction=AlertGamemaster("You notice something!"),
        next_trigger=Trigger(
            event_type="ON_SPOT",
            condition=AlwaysTrue(),
            reaction=ApplyDamage("fire", 4)
        )
    )

    serialized = first_trigger.to_dict()
    deserialized = Trigger.from_dict(serialized)

    assert isinstance(deserialized, Trigger)
    assert deserialized.event_type == "ON_LOOK"
    assert isinstance(deserialized.condition, PerceptionCheck)
    assert deserialized.condition.dc == 10
    assert isinstance(deserialized.reaction, AlertGamemaster)
    assert deserialized.reaction.message == "You notice something!"

    assert deserialized.next_trigger is not None
    assert deserialized.next_trigger.event_type == "ON_SPOT"
    assert isinstance(deserialized.next_trigger.condition, AlwaysTrue)
    assert isinstance(deserialized.next_trigger.reaction, ApplyDamage)
    assert deserialized.next_trigger.reaction.amount == 4
    assert deserialized.next_trigger.reaction.damage_type == "fire"


def test_trigger_chain_reaction_execution(capfd):
    target = DummyTarget()
    data = {"perception": 12, "target": target}

    chain = Trigger(
        event_type="CHAINED",
        condition=AlwaysTrue(),
        reaction=ApplyDamage("ice", 6)
    )

    initial = Trigger(
        event_type="LOOK",
        condition=PerceptionCheck(dc=10),
        reaction=AlertGamemaster("You see something!"),
        next_trigger=chain
    )

    initial.check_and_react(data)

    captured = capfd.readouterr()
    assert "[GM ALERT] You see something!" in captured.out
    assert ("ice", 6) in target.damage_log

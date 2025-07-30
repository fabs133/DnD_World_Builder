import pytest
from core.gameCreation.event_bus import EventBus
from core.gameCreation.trigger import Trigger
from models.flow.condition.condition_list import AlwaysTrue
from models.flow.reaction.reactions_list import ApplyDamage
from models.entities.game_entity import GameEntity

class ChainEntity(GameEntity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.damage_log = []

    def take_damage(self, amount, damage_type):
        self.damage_log.append((damage_type, amount))

@pytest.fixture(autouse=True)
def reset_eventbus():
    EventBus.reset()

def test_trigger_chains_to_next():
    target = ChainEntity(name="Fighter", entity_type="player")

    # Create second trigger that only applies damage
    secondary_trigger = Trigger(
        event_type="CHAINED_EVENT",
        condition=AlwaysTrue(),
        reaction=ApplyDamage("fire", 5)
    )

    # Primary trigger, which leads to the chained one
    primary_trigger = Trigger(
        event_type="ON_STRIKE",
        condition=AlwaysTrue(),
        reaction=lambda event_data: EventBus.emit("CHAINED_EVENT", event_data),
        next_trigger=secondary_trigger
    )

    target.register_trigger(primary_trigger)
    target.register_trigger(secondary_trigger)

    EventBus.emit("ON_STRIKE", {"target": target})

    assert ("fire", 5) in target.damage_log

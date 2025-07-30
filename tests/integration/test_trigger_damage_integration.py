from core.gameCreation.event_bus import EventBus
from core.gameCreation.trigger import Trigger
from models.flow.reaction.reactions_list import ApplyDamage
from models.entities.game_entity import GameEntity


def test_trigger_applies_damage():
    # Create target GameEntity with basic health
    class CombatEntity(GameEntity):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.damage_log = []

        def take_damage(self, amount, damage_type):
            self.damage_log.append((damage_type, amount))

    goblin = CombatEntity(name="Goblin", entity_type="enemy")

    # Set up a trigger that applies damage
    reaction = ApplyDamage(damage_type="piercing", amount=5)
    trigger = Trigger("ON_HIT", condition=lambda data: True, reaction=reaction)

    # Register the trigger to the entity
    goblin.register_trigger(trigger)

    # Simulate the event
    EventBus.emit("ON_HIT", {"target": goblin})

    # Assert the entity took the expected damage
    assert ("piercing", 5) in goblin.damage_log

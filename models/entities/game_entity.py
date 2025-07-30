from core.gameCreation.trigger import Trigger
from registries.trigger_registry import global_trigger_registry
from enum import Enum
from core.logger import app_logger
from core.gameCreation.event_bus import EventBus


class GameEntity:
    """
    Represents a game entity with stats, inventory, and triggers.

    :param name: The name of the entity.
    :type name: str
    :param entity_type: The type/category of the entity.
    :type entity_type: str
    :param stats: The stats dictionary for the entity.
    :type stats: dict, optional
    :param inventory: The inventory list for the entity.
    :type inventory: list, optional
    """

    def __init__(self, name, entity_type, stats=None, inventory=None):
        """
        Initialize a GameEntity instance.

        :param name: The name of the entity.
        :type name: str
        :param entity_type: The type/category of the entity.
        :type entity_type: str
        :param stats: The stats dictionary for the entity.
        :type stats: dict, optional
        :param inventory: The inventory list for the entity.
        :type inventory: list, optional
        """
        self.vision_range = None
        self.name = name
        self.entity_type = entity_type
        self.stats = stats or {}
        self.inventory = inventory or []
        self.triggers = []

    def register_trigger(self, trigger):
        """
        Register a trigger for this entity if not already registered.

        :param trigger: The trigger to register.
        :type trigger: Trigger
        """
        if global_trigger_registry.is_registered(trigger):
            app_logger.debug(f"[Trigger] Already registered: {trigger.label}")
        else:
            global_trigger_registry.add_trigger(trigger, source=self.name)
            EventBus.subscribe(trigger.event_type, trigger.check_and_react)
            app_logger.info(f"[Entity] {self.name} registered trigger: {trigger.label}")

        if all(trigger is not t for t in self.triggers):
            self.triggers.append(trigger)

    def to_dict(self):
        """
        Serialize the entity to a dictionary.

        :return: Dictionary representation of the entity.
        :rtype: dict
        """
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "stats": self.stats,
            "inventory": self.inventory,
            "triggers": [t.to_dict() for t in self.triggers],
        }

    def handle_event(self, event_type, data):
        """
        Handle a tile-based event by running any triggers matching event_type.

        :param event_type: The type of event to handle.
        :type event_type: str
        :param data: Data associated with the event.
        :type data: Any
        """
        for trigger in self.triggers:
            if trigger.event_type == event_type:
                trigger.check_and_react(data)

    @classmethod
    def from_dict(cls, data):
        """
        Create a GameEntity instance from a dictionary.

        :param data: Dictionary containing entity data.
        :type data: dict
        :return: A GameEntity instance.
        :rtype: GameEntity
        """
        obj = cls(
            name=data["name"],
            entity_type=data["entity_type"],
            stats=data.get("stats", {}),
            inventory=data.get("inventory", [])
        )
        for tdata in data.get("triggers", []):
            trigger = Trigger.from_dict(tdata)
            obj.register_trigger(trigger)
        return obj

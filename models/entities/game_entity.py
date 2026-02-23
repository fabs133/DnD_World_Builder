from __future__ import annotations

from typing import TYPE_CHECKING

from core.gameCreation.trigger import Trigger
from registries.trigger_registry import global_trigger_registry
from enum import Enum
from core.logger import app_logger
from core.gameCreation.event_bus import EventBus

if TYPE_CHECKING:
    from models.ai.personality import EntityPersonality


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

    def __init__(self, name, entity_type, stats=None, inventory=None, image_path=None):
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
        :param image_path: Relative path to a portrait image for the entity.
        :type image_path: str, optional
        """
        self.vision_range = None
        self.name = name
        self.entity_type = entity_type
        self.stats = stats or {}
        self.inventory = inventory or []
        self.triggers = []
        self.image_path = image_path
        self.personality: EntityPersonality | None = None
        self.position: tuple[int, int] | None = None
        self.hp: int = self.stats.get("hp", self.stats.get("hit_points", 10))
        self.max_hp: int = self.stats.get("max_hp", self.hp)
        self.conditions: list[str] = []

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
        data = {
            "name": self.name,
            "entity_type": self.entity_type,
            "stats": self.stats,
            "inventory": self.inventory,
            "triggers": [t.to_dict() for t in self.triggers],
            "hp": self.hp,
            "max_hp": self.max_hp,
            "conditions": self.conditions,
        }
        if self.image_path:
            data["image_path"] = self.image_path
        if self.position:
            data["position"] = self.position
        if self.personality:
            data["personality"] = self.personality.to_dict()
        return data

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
            inventory=data.get("inventory", []),
            image_path=data.get("image_path"),
        )
        for tdata in data.get("triggers", []):
            trigger = Trigger.from_dict(tdata)
            obj.register_trigger(trigger)
        
        # Restore HP and conditions
        if "hp" in data:
            obj.hp = data["hp"]
        if "max_hp" in data:
            obj.max_hp = data["max_hp"]
        if "conditions" in data:
            obj.conditions = data["conditions"]
        if "position" in data:
            obj.position = tuple(data["position"])
        
        # Restore personality
        if "personality" in data:
            from models.ai.personality import EntityPersonality
            obj.personality = EntityPersonality.from_dict(data["personality"])
        
        return obj
    
    def set_personality(self, personality: "EntityPersonality") -> None:
        """Set the AI personality for this entity."""
        self.personality = personality
    
    def take_damage(self, amount: int, damage_type: str = "untyped") -> int:
        """Apply damage to this entity. Returns actual damage dealt."""
        actual = min(amount, self.hp)
        self.hp -= actual
        app_logger.debug(f"{self.name} takes {actual} {damage_type} damage. HP: {self.hp}/{self.max_hp}")
        return actual
    
    def heal(self, amount: int) -> int:
        """Heal this entity. Returns actual healing done."""
        actual = min(amount, self.max_hp - self.hp)
        self.hp += actual
        app_logger.debug(f"{self.name} heals {actual}. HP: {self.hp}/{self.max_hp}")
        return actual
    
    @property
    def is_alive(self) -> bool:
        """Check if entity is alive (HP > 0)."""
        return self.hp > 0
    
    @property
    def hp_percent(self) -> float:
        """Current HP as a percentage."""
        if self.max_hp <= 0:
            return 0.0
        return self.hp / self.max_hp

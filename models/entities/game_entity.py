from __future__ import annotations

from typing import TYPE_CHECKING

from core.gameCreation.trigger import Trigger
from registries.trigger_registry import global_trigger_registry
from enum import Enum
from core.logger import app_logger
from core.gameCreation.event_bus import EventBus
from models.entities.entity_type import EntityType

if TYPE_CHECKING:
    from models.ai.personality import EntityPersonality


    # Canonical stat names (D&D 5e standard, title case for abilities)
_STAT_ALIASES: dict[str, str] = {
    # Strength
    "str": "Strength", "STR": "Strength", "strength": "Strength",
    # Dexterity
    "dex": "Dexterity", "DEX": "Dexterity", "dexterity": "Dexterity",
    # Constitution
    "con": "Constitution", "CON": "Constitution", "constitution": "Constitution",
    # Intelligence
    "int": "Intelligence", "INT": "Intelligence", "intelligence": "Intelligence",
    # Wisdom
    "wis": "Wisdom", "WIS": "Wisdom", "wisdom": "Wisdom",
    # Charisma
    "cha": "Charisma", "CHA": "Charisma", "charisma": "Charisma",
    # HP variants
    "hit_points": "hp",
    # AC variants
    "ac": "armor_class",
}


def _normalize_item(item) -> dict:
    """Ensure an inventory item is a dict with name/type/gold_value."""
    if isinstance(item, dict):
        return {
            "name": item.get("name", str(item)),
            "type": item.get("type", item.get("item_type", "trinket")),
            "gold_value": item.get("gold_value", 0),
        }
    return {"name": str(item), "type": "trinket", "gold_value": 0}


def _normalize_stats(stats: dict) -> dict:
    """Canonicalize stat key names to prevent lookup mismatches.

    Maps shorthand and case variants (e.g. ``"dex"``, ``"DEX"``) to their
    canonical form (``"Dexterity"``).  If both an alias and the canonical
    key already exist, the canonical key's value is kept.
    """
    if not isinstance(stats, dict):
        return stats
    normalized: dict = {}
    for key, value in stats.items():
        canonical = _STAT_ALIASES.get(key, key)
        if canonical not in normalized:
            normalized[canonical] = value
    return normalized


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
        # Normalize to EntityType enum when possible; preserve unknown types as-is
        if isinstance(entity_type, EntityType):
            self.entity_type = entity_type
        else:
            try:
                self.entity_type = EntityType(str(entity_type).lower())
            except (ValueError, AttributeError):
                self.entity_type = entity_type
        self.stats = _normalize_stats(stats or {})
        self.inventory = [_normalize_item(i) for i in (inventory or [])]
        self.triggers = []
        self.image_path = image_path
        self.personality: EntityPersonality | None = None
        self._position: tuple[int, int] | None = None
        # Ensure core stats have defaults in the stats dict (single source of truth)
        self.stats.setdefault("hp", 10)
        self.stats.setdefault("max_hp", self.stats["hp"])
        self.stats.setdefault("armor_class", 10)
        self.stats.setdefault("speed", 30)
        self.conditions: list[str] = []
        self.spells: list = self.stats.get("spells", [])
        self.spell_slots = self.stats.get("spell_slots", 0)
        self.spellcasting_ability: str = self.stats.get("spellcasting_ability", "")
        self.spell_attack_bonus: int = self.stats.get("spell_attack_bonus", 0)
        self.portraits: dict[str, str] = {}
        self.voice_profile = None  # Optional[VoiceProfile]
        self.voice_lines_dir: str | None = None
        self.dialogue_lines: dict[str, list[str]] = {}
        self.dialogue_graph = None  # Optional[DialogueGraph]
        self.dialogue_flags: dict[str, bool] = {}

    # -- Core combat stats as properties backed by self.stats ----------------

    @property
    def hp(self) -> int:
        return self.stats.get("hp", 10)

    @hp.setter
    def hp(self, value: int):
        self.stats["hp"] = value

    @property
    def max_hp(self) -> int:
        return self.stats.get("max_hp", self.hp)

    @max_hp.setter
    def max_hp(self, value: int):
        self.stats["max_hp"] = value

    @property
    def armor_class(self) -> int:
        return self.stats.get("armor_class", 10)

    @armor_class.setter
    def armor_class(self, value: int):
        self.stats["armor_class"] = value

    @property
    def speed(self) -> int:
        return self.stats.get("speed", 30)

    @speed.setter
    def speed(self, value: int):
        self.stats["speed"] = value

    @property
    def position(self) -> tuple[int, int] | None:
        return self._position

    @position.setter
    def position(self, value):
        if value is None:
            self._position = None
            return
        if isinstance(value, (list, tuple)) and len(value) == 2:
            self._position = (int(value[0]), int(value[1]))
        else:
            raise ValueError(f"position must be a (x, y) pair or None, got {value!r}")

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
            "entity_type": self.entity_type.value if isinstance(self.entity_type, EntityType) else self.entity_type,
            "stats": self.stats,
            "inventory": self.inventory,
            "triggers": [t.to_dict() for t in self.triggers],
            "hp": self.hp,
            "max_hp": self.max_hp,
            "armor_class": self.armor_class,
            "speed": self.speed,
            "conditions": self.conditions,
        }
        if self.image_path:
            data["image_path"] = self.image_path
        if self.portraits:
            data["portraits"] = self.portraits
        if self.position:
            data["position"] = self.position
        if self.personality:
            data["personality"] = self.personality.to_dict()
        if self.voice_profile:
            data["voice_profile"] = self.voice_profile.to_dict()
        if self.voice_lines_dir:
            data["voice_lines_dir"] = self.voice_lines_dir
        if self.dialogue_lines:
            data["dialogue_lines"] = self.dialogue_lines
        if self.dialogue_graph:
            data["dialogue_graph"] = self.dialogue_graph.to_dict()
        if self.dialogue_flags:
            data["dialogue_flags"] = self.dialogue_flags
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
        if "armor_class" in data:
            obj.armor_class = data["armor_class"]
        elif "ac" in data:
            obj.armor_class = data["ac"]
        if "speed" in data:
            obj.speed = data["speed"]
        if "conditions" in data:
            obj.conditions = data["conditions"]
        if "position" in data:
            obj.position = tuple(data["position"])
        
        # Restore personality
        if "personality" in data:
            from models.ai.personality import EntityPersonality
            obj.personality = EntityPersonality.from_dict(data["personality"])

        # Restore voice — preset ID takes priority (always picks up latest
        # reference audio and params from the registry), falling back to
        # a saved voice_profile dict, then auto-selection from tags.
        if "voice_preset" in data:
            from core.voice.voice_preset_registry import get_preset
            preset = get_preset(data["voice_preset"])
            if preset:
                obj.voice_profile = preset.to_voice_profile()
        elif "voice_profile" in data:
            from core.voice.voice_profile import VoiceProfile
            obj.voice_profile = VoiceProfile.from_dict(data["voice_profile"])
        elif data.get("dialogue_lines"):
            # Auto-select preset from entity tags when no voice is explicitly set
            from core.voice.voice_preset_registry import auto_select_preset
            preset = auto_select_preset(
                entity_name=data.get("name", ""),
                entity_type=data.get("entity_type", ""),
                gender=data.get("gender", ""),
                role=data.get("role", ""),
            )
            if preset:
                obj.voice_profile = preset.to_voice_profile()
        obj.dialogue_lines = data.get("dialogue_lines", {})
        obj.portraits = data.get("portraits", {})
        obj.voice_lines_dir = data.get("voice_lines_dir")

        # Restore dialogue graph — explicit graph first, auto-convert from lines
        if "dialogue_graph" in data:
            from models.dialogue.dialogue_graph import DialogueGraph
            obj.dialogue_graph = DialogueGraph.from_dict(data["dialogue_graph"])
        elif obj.dialogue_lines:
            from models.dialogue.dialogue_graph import DialogueGraph
            obj.dialogue_graph = DialogueGraph.from_dialogue_lines(obj.dialogue_lines)
        obj.dialogue_flags = data.get("dialogue_flags", {})

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
    def is_player(self) -> bool:
        return self.entity_type == EntityType.PLAYER

    @property
    def is_enemy(self) -> bool:
        return self.entity_type in (EntityType.ENEMY, EntityType.MONSTER, EntityType.HOSTILE)

    @property
    def is_friendly(self) -> bool:
        return self.entity_type in (EntityType.PLAYER, EntityType.ALLY, EntityType.COMPANION)

    @property
    def hp_percent(self) -> float:
        """Current HP as a percentage."""
        if self.max_hp <= 0:
            return 0.0
        return self.hp / self.max_hp

"""Extracts and prioritizes dialogue lines from game entities."""

from __future__ import annotations

from enum import IntEnum
from dataclasses import dataclass
from typing import Any, List

from core.voice.voice_profile import VoiceProfile
from core.voice.voice_cache import VoiceCache
from models.entities.entity_type import EntityType


class LinePriority(IntEnum):
    ENTRY_GREETING = 0
    PRIMARY_DIALOGUE = 1
    RESPONSES = 2
    DEEP_DIALOGUE = 3
    COMBAT_CALLOUT = 4


_CATEGORY_PRIORITY = {
    "greeting": LinePriority.ENTRY_GREETING,
    "farewell": LinePriority.ENTRY_GREETING,
    "shop": LinePriority.PRIMARY_DIALOGUE,
    "dialogue": LinePriority.PRIMARY_DIALOGUE,
    "response": LinePriority.RESPONSES,
    "haggle": LinePriority.RESPONSES,
    "quest": LinePriority.DEEP_DIALOGUE,
    "lore": LinePriority.DEEP_DIALOGUE,
    "combat": LinePriority.COMBAT_CALLOUT,
    "threat": LinePriority.COMBAT_CALLOUT,
    "narration": LinePriority.PRIMARY_DIALOGUE,
    "idle": LinePriority.DEEP_DIALOGUE,
}

DEFAULT_NPC_LINES = {
    "greeting": ["Greetings, traveler.", "What brings you here?", "Welcome."],
    "farewell": ["Safe travels.", "Be careful out there.", "Farewell."],
}

DEFAULT_ENEMY_LINES = {
    "combat": ["You will regret this!", "Attack!", "You cannot defeat me!"],
    "threat": ["You shouldn't have come here.", "Leave now, or face the consequences."],
}


@dataclass
class VoiceLine:
    """A single text line that needs voice generation."""
    entity_name: str
    voice_profile: VoiceProfile
    text: str
    line_priority: LinePriority
    category: str
    cache_key: str


class VoiceLineProvider:
    """Extracts and prioritizes dialogue lines from game entities."""

    def get_lines_for_entity(self, entity: Any) -> List[VoiceLine]:
        profile = getattr(entity, "voice_profile", None)
        if not profile or not profile.is_voiced:
            return []

        dialogue = getattr(entity, "dialogue_lines", {})
        if not dialogue:
            entity_type = getattr(entity, "entity_type", "")
            if entity_type in (EntityType.PLAYER,):
                return []
            elif entity_type in (EntityType.ENEMY, EntityType.MONSTER, EntityType.HOSTILE):
                dialogue = DEFAULT_ENEMY_LINES
            else:
                dialogue = DEFAULT_NPC_LINES

        lines = []
        for category, texts in dialogue.items():
            priority = _CATEGORY_PRIORITY.get(category, LinePriority.DEEP_DIALOGUE)
            for text in texts:
                cache_key = VoiceCache.compute_cache_key(
                    profile.voice_id, text,
                    profile.exaggeration, profile.speed_factor, profile.cfg_weight,
                )
                lines.append(VoiceLine(
                    entity_name=entity.name,
                    voice_profile=profile,
                    text=text,
                    line_priority=priority,
                    category=category,
                    cache_key=cache_key,
                ))
        return lines

    def get_lines_for_tile(self, tile_data: Any) -> List[VoiceLine]:
        lines = []
        for entity in getattr(tile_data, "entities", []):
            lines.extend(self.get_lines_for_entity(entity))
        for zone in getattr(tile_data, "zones", []):
            for entity in getattr(zone, "entities", []):
                lines.extend(self.get_lines_for_entity(entity))
        return lines

    def promote_entity_lines(
        self, lines: List[VoiceLine], entity_name: str
    ) -> List[VoiceLine]:
        result = []
        for line in lines:
            if line.entity_name == entity_name:
                result.append(VoiceLine(
                    entity_name=line.entity_name,
                    voice_profile=line.voice_profile,
                    text=line.text,
                    line_priority=LinePriority.ENTRY_GREETING,
                    category=line.category,
                    cache_key=line.cache_key,
                ))
            else:
                result.append(line)
        return result

    def get_combat_lines_for_entities(self, entities: List[Any]) -> List[VoiceLine]:
        lines = []
        for entity in entities:
            for line in self.get_lines_for_entity(entity):
                if line.category in ("combat", "threat"):
                    lines.append(line)
        return lines

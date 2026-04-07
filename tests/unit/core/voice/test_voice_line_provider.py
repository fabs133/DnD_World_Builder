"""Tests for VoiceLineProvider."""

from core.voice.voice_line_provider import VoiceLineProvider, LinePriority
from core.voice.voice_profile import VoiceProfile


class FakeEntity:
    def __init__(self, name, entity_type="npc", voiced=True, dialogue=None):
        self.name = name
        self.entity_type = entity_type
        self.voice_profile = VoiceProfile(
            source_type="preset" if voiced else "none",
            reference_audio="seeds/test.wav" if voiced else None,
        ) if voiced else None
        self.dialogue_lines = dialogue or {}


class FakeTileData:
    def __init__(self, entities=None, zones=None):
        self.entities = entities or []
        self.zones = zones or []


class FakeZone:
    def __init__(self, entities=None):
        self.entities = entities or []


class TestVoiceLineProvider:

    def test_get_lines_for_entity_with_dialogue(self):
        entity = FakeEntity("Bard", dialogue={"greeting": ["Hello!", "Welcome!"]})
        provider = VoiceLineProvider()
        lines = provider.get_lines_for_entity(entity)
        assert len(lines) == 2
        assert lines[0].text == "Hello!"

    def test_falls_back_to_defaults(self):
        entity = FakeEntity("Guard", entity_type="npc")
        provider = VoiceLineProvider()
        lines = provider.get_lines_for_entity(entity)
        assert len(lines) > 0  # default NPC lines

    def test_skips_unvoiced_entity(self):
        entity = FakeEntity("Silent", voiced=False)
        provider = VoiceLineProvider()
        lines = provider.get_lines_for_entity(entity)
        assert len(lines) == 0

    def test_priority_mapping(self):
        entity = FakeEntity("NPC", dialogue={
            "greeting": ["Hi"],
            "combat": ["Attack!"],
        })
        provider = VoiceLineProvider()
        lines = provider.get_lines_for_entity(entity)
        greet = [l for l in lines if l.category == "greeting"][0]
        combat = [l for l in lines if l.category == "combat"][0]
        assert greet.line_priority == LinePriority.ENTRY_GREETING
        assert combat.line_priority == LinePriority.COMBAT_CALLOUT

    def test_tile_includes_zone_entities(self):
        zone_entity = FakeEntity("ZoneNPC", dialogue={"greeting": ["Hello"]})
        tile = FakeTileData(zones=[FakeZone(entities=[zone_entity])])
        provider = VoiceLineProvider()
        lines = provider.get_lines_for_tile(tile)
        assert len(lines) == 1
        assert lines[0].entity_name == "ZoneNPC"

    def test_promote_entity_lines(self):
        entity = FakeEntity("Sage", dialogue={"lore": ["Long ago..."]})
        provider = VoiceLineProvider()
        lines = provider.get_lines_for_entity(entity)
        assert lines[0].line_priority == LinePriority.DEEP_DIALOGUE

        promoted = provider.promote_entity_lines(lines, "Sage")
        assert promoted[0].line_priority == LinePriority.ENTRY_GREETING

    def test_cache_key_computed(self):
        entity = FakeEntity("NPC", dialogue={"greeting": ["Hi"]})
        provider = VoiceLineProvider()
        lines = provider.get_lines_for_entity(entity)
        assert len(lines[0].cache_key) > 0

    def test_combat_lines_only(self):
        entity = FakeEntity("Goblin", entity_type="enemy", dialogue={
            "greeting": ["Die!"],
            "combat": ["Attack!"],
        })
        provider = VoiceLineProvider()
        lines = provider.get_combat_lines_for_entities([entity])
        categories = {l.category for l in lines}
        assert "greeting" not in categories
        assert "combat" in categories

    def test_player_no_default_lines(self):
        entity = FakeEntity("Hero", entity_type="player")
        provider = VoiceLineProvider()
        lines = provider.get_lines_for_entity(entity)
        assert len(lines) == 0

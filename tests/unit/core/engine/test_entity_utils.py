"""Tests for entity name disambiguation and combatant filtering."""

import pytest
from core.engine.entity_utils import disambiguate_names, filter_combatants, is_combatant


class MockEntity:
    def __init__(self, name, entity_type="enemy", hp=10):
        self.name = name
        self.entity_type = entity_type
        self.hp = hp


# ── disambiguate_names ──────────────────────────────────────────────

class TestDisambiguateNames:
    def test_no_duplicates_unchanged(self):
        entities = [MockEntity("Wolf"), MockEntity("Goblin"), MockEntity("Spider")]
        disambiguate_names(entities)
        assert [e.name for e in entities] == ["Wolf", "Goblin", "Spider"]

    def test_duplicates_get_suffixes(self):
        entities = [MockEntity("Wolf"), MockEntity("Wolf"), MockEntity("Wolf")]
        disambiguate_names(entities)
        assert [e.name for e in entities] == ["Wolf 1", "Wolf 2", "Wolf 3"]

    def test_mixed_duplicates_and_unique(self):
        entities = [MockEntity("Wolf"), MockEntity("Goblin"), MockEntity("Wolf")]
        disambiguate_names(entities)
        names = [e.name for e in entities]
        assert names == ["Wolf 1", "Goblin", "Wolf 2"]

    def test_empty_list(self):
        disambiguate_names([])  # Should not raise

    def test_single_entity(self):
        entities = [MockEntity("Dragon")]
        disambiguate_names(entities)
        assert entities[0].name == "Dragon"

    def test_multiple_groups_of_duplicates(self):
        entities = [
            MockEntity("Wolf"), MockEntity("Wolf"),
            MockEntity("Goblin"), MockEntity("Goblin"), MockEntity("Goblin"),
        ]
        disambiguate_names(entities)
        names = [e.name for e in entities]
        assert names == ["Wolf 1", "Wolf 2", "Goblin 1", "Goblin 2", "Goblin 3"]


# ── filter_combatants ───────────────────────────────────────────────

class TestFilterCombatants:
    def test_keeps_players_and_enemies(self):
        entities = [
            MockEntity("Fighter", "player"),
            MockEntity("Goblin", "enemy"),
        ]
        result = filter_combatants(entities)
        assert len(result) == 2

    def test_removes_items(self):
        entities = [
            MockEntity("Fighter", "player"),
            MockEntity("Courier's Satchel", "item"),
            MockEntity("Ancient Sword", "object"),
            MockEntity("Goblin", "enemy"),
        ]
        result = filter_combatants(entities)
        names = [e.name for e in result]
        assert "Fighter" in names
        assert "Goblin" in names
        assert "Courier's Satchel" not in names
        assert "Ancient Sword" not in names

    def test_removes_traps(self):
        entities = [MockEntity("Pit Trap", "trap"), MockEntity("Wolf", "enemy")]
        result = filter_combatants(entities)
        assert len(result) == 1
        assert result[0].name == "Wolf"

    def test_removes_obstacles(self):
        entities = [MockEntity("Pillar", "obstacle"), MockEntity("Wolf", "enemy")]
        result = filter_combatants(entities)
        assert len(result) == 1

    def test_removes_dead(self):
        dead = MockEntity("Skeleton", "enemy", hp=0)
        alive = MockEntity("Zombie", "enemy", hp=10)
        result = filter_combatants([dead, alive])
        assert len(result) == 1
        assert result[0].name == "Zombie"

    def test_keeps_entities_without_hp_attr(self):
        """Entities without an hp attribute are kept (assume alive)."""
        e = MockEntity("Mysterious Figure", "enemy")
        del e.hp
        result = filter_combatants([e])
        assert len(result) == 1

    def test_keeps_npcs(self):
        npc = MockEntity("Shopkeeper", "npc")
        result = filter_combatants([npc])
        assert len(result) == 1

    def test_keeps_allies(self):
        ally = MockEntity("Companion", "ally")
        result = filter_combatants([ally])
        assert len(result) == 1

    def test_keeps_monster_type(self):
        monster = MockEntity("Dragon", "monster")
        result = filter_combatants([monster])
        assert len(result) == 1

    def test_empty_list(self):
        result = filter_combatants([])
        assert result == []


# ── is_combatant ────────────────────────────────────────────────────

class TestIsCombatant:
    def test_player(self):
        assert is_combatant(MockEntity("Fighter", "player")) is True

    def test_enemy(self):
        assert is_combatant(MockEntity("Goblin", "enemy")) is True

    def test_trap(self):
        assert is_combatant(MockEntity("Spike Trap", "trap")) is False

    def test_item(self):
        assert is_combatant(MockEntity("Potion", "item")) is False

    def test_dead_enemy(self):
        assert is_combatant(MockEntity("Skeleton", "enemy", hp=0)) is False

    def test_no_entity_type(self):
        e = MockEntity("Thing", "")
        assert is_combatant(e) is False

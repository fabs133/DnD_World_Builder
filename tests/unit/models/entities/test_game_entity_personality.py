"""Tests for GameEntity personality integration."""

import pytest
from models.entities.game_entity import GameEntity
from models.ai.personality import EntityPersonality
from models.ai.alignment import Alignment


class TestGameEntityPersonality:
    """Test personality integration with GameEntity."""

    def test_entity_has_personality_attribute(self):
        entity = GameEntity("Goblin", "enemy")
        assert hasattr(entity, "personality")
        assert entity.personality is None  # Default

    def test_set_personality(self):
        entity = GameEntity("Paladin", "player")
        personality = EntityPersonality(Alignment.LAWFUL_GOOD)
        entity.set_personality(personality)
        
        assert entity.personality is not None
        assert entity.personality.alignment == Alignment.LAWFUL_GOOD
        assert entity.personality.archetype == "Protector"

    def test_personality_serialization(self):
        entity = GameEntity("Rogue", "player", stats={"hp": 25})
        entity.set_personality(EntityPersonality(
            alignment=Alignment.CHAOTIC_GOOD,
            trait="Sarcastic",
            bond="My friends",
            flaw="Can't resist shiny things",
        ))
        
        data = entity.to_dict()
        
        assert "personality" in data
        assert data["personality"]["alignment"]["law_chaos"] == "chaotic"
        assert data["personality"]["alignment"]["good_evil"] == "good"
        assert data["personality"]["trait"] == "Sarcastic"

    def test_personality_deserialization(self):
        data = {
            "name": "Orc",
            "entity_type": "enemy",
            "stats": {"hp": 15},
            "inventory": [],
            "triggers": [],
            "hp": 15,
            "max_hp": 15,
            "conditions": [],
            "personality": {
                "alignment": {"law_chaos": "chaotic", "good_evil": "evil"},
                "trait": "Bloodthirsty",
                "bond": "",
                "flaw": "Cannot retreat",
                "ideal": "",
                "relationships": {},
            }
        }
        
        entity = GameEntity.from_dict(data)
        
        assert entity.personality is not None
        assert entity.personality.alignment == Alignment.CHAOTIC_EVIL
        assert entity.personality.trait == "Bloodthirsty"

    def test_personality_preset_integration(self):
        entity = GameEntity("Goblin Guard", "enemy", stats={"hp": 7, "max_hp": 7})
        entity.set_personality(EntityPersonality.goblin_grunt())
        
        assert entity.personality.alignment == Alignment.NEUTRAL_EVIL
        # Goblin grunt should be cowardly
        weights = entity.personality.tactical_weights
        assert weights.flee_threshold > 0.4


class TestGameEntityCombat:
    """Test new combat-related GameEntity methods."""

    def test_hp_initialization_from_stats(self):
        entity = GameEntity("Fighter", "player", stats={"hp": 30, "max_hp": 30})
        assert entity.hp == 30
        assert entity.max_hp == 30

    def test_hp_initialization_fallback(self):
        entity = GameEntity("Unknown", "npc", stats={})
        assert entity.hp == 10  # Default
        assert entity.max_hp == 10

    def test_take_damage(self):
        entity = GameEntity("Fighter", "player", stats={"hp": 30, "max_hp": 30})
        actual = entity.take_damage(10)
        
        assert actual == 10
        assert entity.hp == 20

    def test_take_damage_overkill(self):
        entity = GameEntity("Goblin", "enemy", stats={"hp": 5, "max_hp": 5})
        actual = entity.take_damage(20)
        
        assert actual == 5  # Can't deal more than HP
        assert entity.hp == 0

    def test_heal(self):
        entity = GameEntity("Cleric", "player", stats={"hp": 20, "max_hp": 30})
        entity.hp = 10
        actual = entity.heal(15)
        
        assert actual == 15
        assert entity.hp == 25

    def test_heal_overheal(self):
        entity = GameEntity("Cleric", "player", stats={"hp": 25, "max_hp": 30})
        actual = entity.heal(100)
        
        assert actual == 5  # Only heals to max
        assert entity.hp == 30

    def test_is_alive(self):
        entity = GameEntity("Warrior", "player", stats={"hp": 10})
        assert entity.is_alive is True
        
        entity.hp = 0
        assert entity.is_alive is False

    def test_hp_percent(self):
        entity = GameEntity("Test", "npc", stats={"hp": 50, "max_hp": 100})
        entity.hp = 50
        entity.max_hp = 100
        assert entity.hp_percent == 0.5
        
        entity.hp = 25
        assert entity.hp_percent == 0.25

    def test_conditions(self):
        entity = GameEntity("Target", "enemy")
        assert entity.conditions == []
        
        entity.conditions.append("poisoned")
        entity.conditions.append("prone")
        
        data = entity.to_dict()
        assert "poisoned" in data["conditions"]
        assert "prone" in data["conditions"]

    def test_position(self):
        entity = GameEntity("Ranger", "player")
        entity.position = (5, 10)
        
        data = entity.to_dict()
        assert data["position"] == (5, 10)
        
        restored = GameEntity.from_dict(data)
        assert restored.position == (5, 10)

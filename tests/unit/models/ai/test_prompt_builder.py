# tests/unit/models/ai/test_prompt_builder.py
"""Tests for the tactical prompt builder."""

import pytest
from models.ai.alignment import Alignment
from models.ai.personality import EntityPersonality
from models.ai.prompt_builder import (
    TacticalPromptBuilder,
    CombatMemory,
    CombatantInfo,
    ActionOption,
)


class TestCombatMemory:
    """Test combat memory tracking."""
    
    def test_record_damage_taken(self):
        memory = CombatMemory()
        memory.record_damage_taken("Goblin", 5)
        memory.record_damage_taken("Goblin", 3)
        
        assert memory.damage_taken_from["Goblin"] == 8
    
    def test_record_ally_damage(self):
        memory = CombatMemory()
        memory.record_ally_damage("Wizard", "Fighter", 10)
        
        assert memory.witnessed_ally_damage["Wizard"] == 10
    
    def test_record_healing(self):
        memory = CombatMemory()
        memory.record_healing("Cleric", 8)
        
        assert memory.healed_by["Cleric"] == 8
    
    def test_record_ally_fallen(self):
        memory = CombatMemory()
        memory.record_ally_fallen("Guard A")
        memory.record_ally_fallen("Guard A")  # Duplicate should be ignored
        
        assert memory.fallen_allies == ["Guard A"]
    
    def test_record_kill(self):
        memory = CombatMemory()
        memory.record_kill("Goblin")
        
        assert "Goblin" in memory.kills
    
    def test_recent_events_limited(self):
        memory = CombatMemory()
        for i in range(10):
            memory.record_damage_taken(f"Enemy{i}", 1)
        
        # Should only keep last N events
        assert len(memory.recent_events) == CombatMemory.MAX_RECENT_EVENTS
    
    def test_get_grudge_target(self):
        memory = CombatMemory()
        memory.record_damage_taken("Wizard", 15)
        memory.record_damage_taken("Fighter", 5)
        memory.record_ally_damage("Wizard", "Guard", 10)
        
        # Wizard dealt 15 direct + 5 (0.5 * 10) witnessed = 20 total
        # Fighter dealt 5
        grudge = memory.get_grudge_target()
        assert grudge == "Wizard"
    
    def test_grudge_target_none_if_no_damage(self):
        memory = CombatMemory()
        assert memory.get_grudge_target() is None
    
    def test_grudge_target_none_if_insignificant(self):
        memory = CombatMemory()
        memory.record_damage_taken("Weak", 2)  # Below threshold
        assert memory.get_grudge_target() is None
    
    def test_format_for_prompt_with_grudge(self):
        memory = CombatMemory()
        memory.record_damage_taken("Fighter", 10)
        memory.record_ally_fallen("Guard A")
        
        text = memory.format_for_prompt()
        
        assert "GRUDGE TARGET: Fighter" in text
        assert "FALLEN ALLIES: Guard A" in text
    
    def test_serialization_roundtrip(self):
        memory = CombatMemory()
        memory.record_damage_taken("Enemy", 10)
        memory.record_kill("Minion")
        
        data = memory.to_dict()
        restored = CombatMemory.from_dict(data)
        
        assert restored.damage_taken_from["Enemy"] == 10
        assert "Minion" in restored.kills


class TestCombatantInfo:
    """Test combatant info formatting."""
    
    def test_hp_percent(self):
        c = CombatantInfo("Test", "enemy", 50, 100, (0, 0))
        assert c.hp_percent == 0.5
    
    def test_hp_status_healthy(self):
        c = CombatantInfo("Test", "enemy", 95, 100, (0, 0))
        assert c.hp_status == "healthy"
    
    def test_hp_status_wounded(self):
        c = CombatantInfo("Test", "enemy", 35, 100, (0, 0))
        assert c.hp_status == "wounded"
    
    def test_hp_status_down(self):
        c = CombatantInfo("Test", "enemy", 0, 100, (0, 0))
        assert c.hp_status == "down"
    
    def test_format_for_prompt(self):
        c = CombatantInfo("Goblin", "enemy", 5, 7, (2, 3), conditions=["poisoned"])
        text = c.format_for_prompt()
        
        assert "Goblin" in text
        assert "5/7 HP" in text
        assert "(2, 3)" in text
        assert "poisoned" in text


class TestActionOption:
    """Test action option formatting."""
    
    def test_format_simple_action(self):
        action = ActionOption("Attack", "Strike with weapon")
        text = action.format_for_prompt(1)
        
        assert "1. Attack:" in text
        assert "Strike with weapon" in text
    
    def test_format_targeted_action(self):
        action = ActionOption(
            "Healing Word",
            "Heal an ally for 1d4+3",
            requires_target=True,
            valid_targets=["Fighter", "Rogue"],
        )
        text = action.format_for_prompt(2)
        
        assert "2. Healing Word:" in text
        assert "Fighter" in text
        assert "Rogue" in text


class TestTacticalPromptBuilder:
    """Test the full prompt builder."""
    
    @pytest.fixture
    def builder(self):
        return TacticalPromptBuilder()
    
    @pytest.fixture
    def personality(self):
        return EntityPersonality(
            alignment=Alignment.NEUTRAL_EVIL,
            trait="Cold and calculating",
            flaw="Self-interested to a fault",
        )
    
    @pytest.fixture
    def allies(self):
        return [
            CombatantInfo("Goblin Guard", "ally", 7, 7, (1, 1), is_ally=True),
        ]
    
    @pytest.fixture
    def enemies(self):
        return [
            CombatantInfo("Fighter", "player", 25, 30, (2, 2)),
            CombatantInfo("Wizard", "player", 8, 14, (4, 4)),
        ]
    
    @pytest.fixture
    def actions(self):
        return [
            ActionOption("Attack", "Strike with dagger (1d4+2)"),
            ActionOption("Vicious Mockery", "Deal 1d4 psychic damage"),
            ActionOption("Flee", "Disengage and run"),
        ]
    
    def test_build_action_prompt_contains_alignment(self, builder, personality, allies, enemies, actions):
        prompt = builder.build_action_prompt(
            actor_name="Goblin Shaman",
            actor_type="goblin spellcaster",
            actor_hp=(12, 12),
            actor_position=(3, 3),
            personality=personality,
            allies=allies,
            enemies=enemies,
            available_actions=actions,
        )
        
        assert "Neutral Evil" in prompt
        assert "Mercenary" in prompt
    
    def test_build_action_prompt_contains_situation(self, builder, personality, allies, enemies, actions):
        prompt = builder.build_action_prompt(
            actor_name="Goblin Shaman",
            actor_type="goblin spellcaster",
            actor_hp=(12, 12),
            actor_position=(3, 3),
            personality=personality,
            allies=allies,
            enemies=enemies,
            available_actions=actions,
        )
        
        assert "YOUR STATUS:" in prompt
        assert "12/12 HP" in prompt
        assert "ALLIES:" in prompt
        assert "Goblin Guard" in prompt
        assert "ENEMIES:" in prompt
        assert "Fighter" in prompt
        assert "Wizard" in prompt
    
    def test_build_action_prompt_contains_actions(self, builder, personality, allies, enemies, actions):
        prompt = builder.build_action_prompt(
            actor_name="Goblin Shaman",
            actor_type="goblin spellcaster",
            actor_hp=(12, 12),
            actor_position=(3, 3),
            personality=personality,
            allies=allies,
            enemies=enemies,
            available_actions=actions,
        )
        
        assert "AVAILABLE ACTIONS" in prompt
        assert "Attack" in prompt
        assert "Vicious Mockery" in prompt
        assert "Flee" in prompt
    
    def test_build_action_prompt_contains_json_instructions(self, builder, personality, allies, enemies, actions):
        prompt = builder.build_action_prompt(
            actor_name="Goblin Shaman",
            actor_type="goblin spellcaster",
            actor_hp=(12, 12),
            actor_position=(3, 3),
            personality=personality,
            allies=allies,
            enemies=enemies,
            available_actions=actions,
        )
        
        assert '"action":' in prompt
        assert '"reasoning":' in prompt
        assert "JSON" in prompt
    
    def test_build_action_prompt_with_memory(self, builder, personality, allies, enemies, actions):
        memory = CombatMemory()
        memory.record_damage_taken("Fighter", 10)
        memory.record_ally_fallen("Goblin Scout")
        
        prompt = builder.build_action_prompt(
            actor_name="Goblin Shaman",
            actor_type="goblin spellcaster",
            actor_hp=(8, 12),
            actor_position=(3, 3),
            personality=personality,
            allies=allies,
            enemies=enemies,
            available_actions=actions,
            memory=memory,
        )
        
        assert "GRUDGE TARGET: Fighter" in prompt
        assert "Goblin Scout" in prompt
    
    def test_build_action_prompt_with_additional_context(self, builder, personality, allies, enemies, actions):
        prompt = builder.build_action_prompt(
            actor_name="Goblin Shaman",
            actor_type="goblin spellcaster",
            actor_hp=(12, 12),
            actor_position=(3, 3),
            personality=personality,
            allies=allies,
            enemies=enemies,
            available_actions=actions,
            additional_context="There is a trap at position (2, 3). The altar provides half cover.",
        )
        
        assert "trap" in prompt
        assert "altar" in prompt
    
    def test_build_simple_prompt(self, builder, personality):
        prompt = builder.build_simple_prompt(
            situation="You see a wounded traveler on the road. They have a heavy coin purse.",
            personality=personality,
            options=["Help them", "Rob them", "Ignore them"],
        )
        
        assert "Neutral Evil" in prompt
        assert "wounded traveler" in prompt
        assert "Help them" in prompt
        assert "Rob them" in prompt
        assert '"choice":' in prompt


class TestPromptBuilderEdgeCases:
    """Test edge cases and configuration."""
    
    def test_no_allies(self):
        builder = TacticalPromptBuilder()
        personality = EntityPersonality(Alignment.TRUE_NEUTRAL)
        
        prompt = builder.build_action_prompt(
            actor_name="Lone Wolf",
            actor_type="wolf",
            actor_hp=(15, 15),
            actor_position=(0, 0),
            personality=personality,
            allies=[],  # No allies
            enemies=[CombatantInfo("Hunter", "player", 20, 20, (1, 1))],
            available_actions=[ActionOption("Bite", "1d6+3 damage")],
        )
        
        assert "ALLIES: None" in prompt
    
    def test_no_actions(self):
        builder = TacticalPromptBuilder()
        personality = EntityPersonality(Alignment.TRUE_NEUTRAL)
        
        prompt = builder.build_action_prompt(
            actor_name="Stunned",
            actor_type="creature",
            actor_hp=(10, 10),
            actor_position=(0, 0),
            personality=personality,
            allies=[],
            enemies=[],
            available_actions=[],  # No actions
        )
        
        assert "PASS" in prompt
    
    def test_disable_voice_lines(self):
        builder = TacticalPromptBuilder(include_voice_lines=False)
        personality = EntityPersonality(Alignment.CHAOTIC_EVIL)
        
        prompt = builder.build_action_prompt(
            actor_name="Quiet Villain",
            actor_type="villain",
            actor_hp=(50, 50),
            actor_position=(0, 0),
            personality=personality,
            allies=[],
            enemies=[],
            available_actions=[ActionOption("Scheme", "Plot quietly")],
        )
        
        # Should not contain voice lines
        assert "EXAMPLE VOICE LINE" not in prompt
    
    def test_disable_memory(self):
        builder = TacticalPromptBuilder(include_memory=False)
        personality = EntityPersonality(Alignment.TRUE_NEUTRAL)
        memory = CombatMemory()
        memory.record_damage_taken("Enemy", 100)
        
        prompt = builder.build_action_prompt(
            actor_name="Forgetful",
            actor_type="creature",
            actor_hp=(10, 10),
            actor_position=(0, 0),
            personality=personality,
            allies=[],
            enemies=[],
            available_actions=[ActionOption("Attack", "Hit")],
            memory=memory,
        )
        
        assert "GRUDGE" not in prompt
        assert "COMBAT MEMORY" not in prompt

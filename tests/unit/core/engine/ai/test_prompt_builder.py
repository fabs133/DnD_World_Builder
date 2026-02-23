"""Tests for TacticalPromptBuilder (alignment-based prompt system)."""

from core.engine.ai.prompt_builder import TacticalPromptBuilder, CombatantInfo, ActionOption
from core.engine.ai import AGGRESSIVE, DEFENSIVE, EntityPersonality, Alignment
from core.engine.game_state import GameState, EntitySnapshot


def _make_state():
    fighter = EntitySnapshot(
        name="Fighter", entity_type="player", hp=20, max_hp=25,
        armor_class=16, position=(0, 0), conditions=(), stats={},
        speed=30, faction="player", is_alive=True,
    )
    goblin = EntitySnapshot(
        name="Goblin", entity_type="enemy", hp=5, max_hp=7,
        armor_class=13, position=(2, 0), conditions=("poisoned",),
        stats={}, speed=30, faction="enemy", is_alive=True,
    )
    cleric = EntitySnapshot(
        name="Cleric", entity_type="player", hp=15, max_hp=18,
        armor_class=14, position=(0, 1), conditions=(), stats={},
        speed=30, faction="player", is_alive=True,
    )
    return GameState(
        round_number=2,
        current_entity_name="Fighter",
        entities=(fighter, goblin, cleric),
        initiative_order=("Fighter", "Goblin", "Cleric"),
        world_width=5, world_height=5, tile_type="square",
    )


class TestTacticalPromptBuilder:
    def test_basic_prompt_structure(self):
        builder = TacticalPromptBuilder()
        personality = EntityPersonality(Alignment.LAWFUL_GOOD)
        prompt = builder.build_action_prompt(
            actor_name="Fighter",
            actor_type="player",
            actor_hp=(20, 25),
            actor_position=(0, 0),
            personality=personality,
            allies=[],
            enemies=[CombatantInfo("Goblin", "enemy", 5, 7, (2, 0))],
            available_actions=[ActionOption("ATTACK", "Attack an enemy", requires_target=True)],
        )

        assert "Fighter" in prompt
        assert "ENEMIES:" in prompt
        assert "Goblin" in prompt
        assert "AVAILABLE ACTIONS" in prompt

    def test_includes_enemy_details(self):
        builder = TacticalPromptBuilder()
        personality = EntityPersonality(Alignment.TRUE_NEUTRAL)
        enemy = CombatantInfo("Goblin", "enemy", 5, 7, (2, 0), conditions=["poisoned"])
        prompt = builder.build_action_prompt(
            actor_name="Fighter",
            actor_type="player",
            actor_hp=(20, 25),
            actor_position=(0, 0),
            personality=personality,
            allies=[],
            enemies=[enemy],
            available_actions=[ActionOption("ATTACK", "Attack")],
        )

        assert "5/7" in prompt
        assert "poisoned" in prompt

    def test_includes_personality(self):
        builder = TacticalPromptBuilder()
        prompt = builder.build_action_prompt(
            actor_name="Fighter",
            actor_type="player",
            actor_hp=(20, 25),
            actor_position=(0, 0),
            personality=AGGRESSIVE,
            allies=[],
            enemies=[CombatantInfo("Goblin", "enemy", 5, 7, (2, 0))],
            available_actions=[ActionOption("ATTACK", "Attack")],
        )

        # AGGRESSIVE maps to Chaotic Evil -> Agent of Chaos archetype
        assert "chaos" in prompt.lower() or "chaotic" in prompt.lower()

    def test_includes_error_context(self):
        builder = TacticalPromptBuilder()
        personality = EntityPersonality(Alignment.TRUE_NEUTRAL)
        prompt = builder.build_action_prompt(
            actor_name="Fighter",
            actor_type="player",
            actor_hp=(20, 25),
            actor_position=(0, 0),
            personality=personality,
            allies=[],
            enemies=[],
            available_actions=[ActionOption("ATTACK", "Attack")],
            additional_context="PREVIOUS ATTEMPT FAILED: Target not found",
        )

        assert "PREVIOUS ATTEMPT FAILED" in prompt
        assert "Target not found" in prompt

    def test_missing_entity_builds_prompt(self):
        builder = TacticalPromptBuilder()
        personality = EntityPersonality(Alignment.TRUE_NEUTRAL)
        prompt = builder.build_action_prompt(
            actor_name="Unknown",
            actor_type="creature",
            actor_hp=(10, 10),
            actor_position=(0, 0),
            personality=personality,
            allies=[],
            enemies=[],
            available_actions=[ActionOption("END_TURN", "End turn")],
        )

        assert "Unknown" in prompt

    def test_includes_allies(self):
        builder = TacticalPromptBuilder()
        personality = EntityPersonality(Alignment.LAWFUL_GOOD)
        ally = CombatantInfo("Cleric", "player", 15, 18, (0, 1), is_ally=True)
        prompt = builder.build_action_prompt(
            actor_name="Fighter",
            actor_type="player",
            actor_hp=(20, 25),
            actor_position=(0, 0),
            personality=personality,
            allies=[ally],
            enemies=[],
            available_actions=[ActionOption("END_TURN", "End turn")],
        )

        assert "ALLIES:" in prompt
        assert "Cleric" in prompt

    def test_defensive_personality_content(self):
        builder = TacticalPromptBuilder()
        prompt = builder.build_action_prompt(
            actor_name="Paladin",
            actor_type="player",
            actor_hp=(30, 30),
            actor_position=(0, 0),
            personality=DEFENSIVE,
            allies=[],
            enemies=[],
            available_actions=[ActionOption("END_TURN", "End turn")],
        )

        # DEFENSIVE maps to Lawful Good -> Protector archetype
        assert "Protector" in prompt

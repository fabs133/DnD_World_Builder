"""Tests for combat_factory."""

from models.combat.combat_factory import create_combat_instance
from models.combat.encounter_template import EncounterTemplate, EnemySpawn
from models.combat.combat_instance import CombatState
from models.combat.combatant import CombatantFaction


class FakePlayerEntity:
    def __init__(self, name, hp=20):
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.speed = 30
        self.entity_type = "player"


class TestCombatFactory:

    def test_create_instance_from_template(self):
        template = EncounterTemplate(
            template_id="t1",
            name="Test Fight",
            grid_width=5,
            grid_height=5,
            enemy_spawns=[
                EnemySpawn(position=(4, 0), creature_index="goblin", count=2),
            ],
            player_spawn_zone=[(0, 4), (1, 4)],
        )
        players = [FakePlayerEntity("Hero"), FakePlayerEntity("Rogue")]
        instance = create_combat_instance(template, players, seed=42)

        assert instance.state == CombatState.SETUP
        assert instance.template_id == "t1"
        assert instance.template_name == "Test Fight"
        # 2 goblins + 2 players = 4 combatants
        assert len(instance.combatants) == 4

    def test_players_placed_in_spawn_zone(self):
        template = EncounterTemplate(
            template_id="t",
            name="T",
            player_spawn_zone=[(0, 4), (1, 4)],
        )
        players = [FakePlayerEntity("A"), FakePlayerEntity("B")]
        instance = create_combat_instance(template, players)

        player_combatants = [c for c in instance.combatants if c.faction == CombatantFaction.PLAYER]
        assert player_combatants[0].position == (0, 4)
        assert player_combatants[1].position == (1, 4)

    def test_enemy_spawns_resolved(self):
        template = EncounterTemplate(
            template_id="t",
            name="T",
            enemy_spawns=[
                EnemySpawn(position=(3, 1), creature_index="bandit", count=3),
            ],
        )
        instance = create_combat_instance(template, [], seed=42)

        enemies = [c for c in instance.combatants if c.faction == CombatantFaction.ENEMY]
        assert len(enemies) == 3
        for e in enemies:
            assert e.position == (3, 1)
            assert "bandit" in e.name.lower()

    def test_spawn_variance(self):
        template = EncounterTemplate(
            template_id="t",
            name="T",
            enemy_spawns=[
                EnemySpawn(position=(0, 0), creature_index="goblin", count=3, variance=2),
            ],
        )
        # With variance=2, count can be 1-5
        counts = set()
        for seed in range(50):
            instance = create_combat_instance(template, [], seed=seed)
            enemies = [c for c in instance.combatants if c.faction == CombatantFaction.ENEMY]
            counts.add(len(enemies))

        # With 50 seeds and variance=2, we should see at least 2 different counts
        assert len(counts) >= 2

    def test_extra_players_stack_at_last_position(self):
        template = EncounterTemplate(
            template_id="t",
            name="T",
            player_spawn_zone=[(0, 0)],  # Only one spawn position
        )
        players = [FakePlayerEntity("A"), FakePlayerEntity("B"), FakePlayerEntity("C")]
        instance = create_combat_instance(template, players)

        player_combatants = [c for c in instance.combatants if c.faction == CombatantFaction.PLAYER]
        # All should be at (0, 0) since there's only one spawn spot
        for c in player_combatants:
            assert c.position == (0, 0)

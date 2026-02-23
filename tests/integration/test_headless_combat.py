"""Integration test: full headless combat scenario with TestAdapter."""

import pytest
from core.engine.game_session import GameSession
from core.engine.input_adapter import TestAdapter
from core.engine.actions.attack_action import AttackAction
from core.engine.actions.end_turn_action import EndTurnAction
from models.game_master import Gamemaster
from models.world.world import World

import random


class SimpleEntity:
    """Test entity with minimal D&D attributes."""

    def __init__(self, name, entity_type, hp, armor_class=12, speed=30, dex=10):
        self.name = name
        self.entity_type = entity_type
        self.hp = hp
        self.armor_class = armor_class
        self.speed = speed
        self.stats = {"Dexterity": dex, "max_hp": hp}
        self.conditions = []
        self.position = (0, 0)
        self.initiative = 0
        self.triggers = []
        self.inventory = []


class TestHeadlessCombat:
    def test_2v2_scripted_combat(self):
        """Two players vs two goblins - scripted actions, deterministic outcome."""
        gm = Gamemaster()
        gm.world = World(
            world_version=1, width=5, height=5, tile_type="square",
            description="Arena", map_data={}, time_of_day="", weather_conditions="",
        )
        gm.world_tile_manager = gm.world.tile_manager

        fighter = SimpleEntity("Fighter", "player", hp=25, armor_class=16, dex=12)
        wizard = SimpleEntity("Wizard", "player", hp=15, armor_class=12, dex=14)
        goblin1 = SimpleEntity("Goblin1", "enemy", hp=7, armor_class=13, dex=14)
        goblin2 = SimpleEntity("Goblin2", "enemy", hp=7, armor_class=13, dex=14)

        gm.game_entities = [fighter, wizard, goblin1, goblin2]
        gm.world_tile_manager.place_entity(fighter, 0, 0)
        gm.world_tile_manager.place_entity(wizard, 0, 1)
        gm.world_tile_manager.place_entity(goblin1, 4, 0)
        gm.world_tile_manager.place_entity(goblin2, 4, 1)

        rng = random.Random(42)

        # Script: enough actions for up to 5 rounds of combat
        fighter_actions = [
            AttackAction(fighter, goblin1, damage_expr="1d8+3", to_hit_bonus=7, rng=rng),
            AttackAction(fighter, goblin2, damage_expr="1d8+3", to_hit_bonus=7, rng=rng),
            AttackAction(fighter, goblin1, damage_expr="1d8+3", to_hit_bonus=7, rng=rng),
            AttackAction(fighter, goblin2, damage_expr="1d8+3", to_hit_bonus=7, rng=rng),
            AttackAction(fighter, goblin1, damage_expr="1d8+3", to_hit_bonus=7, rng=rng),
        ]
        wizard_actions = [
            AttackAction(wizard, goblin1, damage_expr="2d6", to_hit_bonus=5, rng=rng),
            AttackAction(wizard, goblin2, damage_expr="2d6", to_hit_bonus=5, rng=rng),
            AttackAction(wizard, goblin1, damage_expr="2d6", to_hit_bonus=5, rng=rng),
            AttackAction(wizard, goblin2, damage_expr="2d6", to_hit_bonus=5, rng=rng),
            EndTurnAction(wizard),
        ]
        goblin1_actions = [
            AttackAction(goblin1, fighter, damage_expr="1d6+1", to_hit_bonus=4, rng=rng),
            AttackAction(goblin1, fighter, damage_expr="1d6+1", to_hit_bonus=4, rng=rng),
            AttackAction(goblin1, fighter, damage_expr="1d6+1", to_hit_bonus=4, rng=rng),
            EndTurnAction(goblin1),
            EndTurnAction(goblin1),
        ]
        goblin2_actions = [
            AttackAction(goblin2, wizard, damage_expr="1d6+1", to_hit_bonus=4, rng=rng),
            AttackAction(goblin2, wizard, damage_expr="1d6+1", to_hit_bonus=4, rng=rng),
            AttackAction(goblin2, wizard, damage_expr="1d6+1", to_hit_bonus=4, rng=rng),
            EndTurnAction(goblin2),
            EndTurnAction(goblin2),
        ]

        adapters = {
            "Fighter": TestAdapter(action_sequence=fighter_actions),
            "Wizard": TestAdapter(action_sequence=wizard_actions),
            "Goblin1": TestAdapter(action_sequence=goblin1_actions),
            "Goblin2": TestAdapter(action_sequence=goblin2_actions),
        }

        session = GameSession(gm, adapters, seed=42, max_rounds=5)
        session.setup()

        result = session.run()

        # Verify session completed
        assert result.rounds_played >= 1
        assert result.termination_reason != ""
        assert len(result.action_history) > 0

    def test_deterministic_replay(self):
        """Same seed + same actions produces identical results."""
        def run_combat(seed):
            gm = Gamemaster()
            gm.world = World(
                world_version=1, width=5, height=5, tile_type="square",
                description="", map_data={}, time_of_day="", weather_conditions="",
            )
            gm.world_tile_manager = gm.world.tile_manager

            fighter = SimpleEntity("Fighter", "player", hp=25, armor_class=16)
            goblin = SimpleEntity("Goblin", "enemy", hp=7, armor_class=13)
            gm.game_entities = [fighter, goblin]
            gm.world_tile_manager.place_entity(fighter, 0, 0)
            gm.world_tile_manager.place_entity(goblin, 4, 0)

            rng = random.Random(seed)
            fighter_actions = [
                AttackAction(fighter, goblin, damage_expr="1d8+3", to_hit_bonus=5, rng=rng),
                AttackAction(fighter, goblin, damage_expr="1d8+3", to_hit_bonus=5, rng=rng),
                AttackAction(fighter, goblin, damage_expr="1d8+3", to_hit_bonus=5, rng=rng),
            ]
            goblin_actions = [
                EndTurnAction(goblin),
                EndTurnAction(goblin),
                EndTurnAction(goblin),
            ]
            adapters = {
                "Fighter": TestAdapter(action_sequence=fighter_actions),
                "Goblin": TestAdapter(action_sequence=goblin_actions),
            }

            session = GameSession(gm, adapters, seed=seed, max_rounds=3)
            session.setup()
            return session.run()

        r1 = run_combat(42)
        r2 = run_combat(42)

        assert r1.rounds_played == r2.rounds_played
        assert r1.winner == r2.winner
        assert r1.termination_reason == r2.termination_reason

    def test_combat_callbacks_track_events(self):
        """Verify callback hooks receive correct data."""
        events = []

        gm = Gamemaster()
        fighter = SimpleEntity("Fighter", "player", hp=20)
        goblin = SimpleEntity("Goblin", "enemy", hp=5)
        gm.game_entities = [fighter, goblin]

        rng = random.Random(42)
        fighter_actions = [
            AttackAction(fighter, goblin, damage_expr="2d6+5", to_hit_bonus=10, rng=rng),
        ]
        goblin_actions = [EndTurnAction(goblin)]

        adapters = {
            "Fighter": TestAdapter(action_sequence=fighter_actions),
            "Goblin": TestAdapter(action_sequence=goblin_actions),
        }

        session = GameSession(
            gm, adapters, seed=42, max_rounds=3,
            on_round_start=lambda s: events.append(("round_start", s.round_number)),
            on_turn_start=lambda s, n: events.append(("turn", n)),
            on_action_result=lambda r: events.append(("action", r.success)),
            on_round_end=lambda s: events.append(("round_end", s.round_number)),
        )
        session.setup()
        session.run()

        round_starts = [e for e in events if e[0] == "round_start"]
        assert len(round_starts) >= 1
        turns = [e for e in events if e[0] == "turn"]
        assert len(turns) >= 1

"""Tests for HeuristicAIAdapter — deterministic AI without Ollama."""

import random

import pytest

from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
from core.engine.game_state import GameState, EntitySnapshot
from core.engine.actions.attack_action import AttackAction
from core.engine.actions.move_action import MoveAction
from core.engine.actions.end_turn_action import EndTurnAction
from models.ai.personality import EntityPersonality
from models.ai.alignment import Alignment
from models.ai.tactical_weights import TacticalWeights


# ── Helpers ──────────────────────────────────────────────────────────────


class SimpleEntity:
    def __init__(self, name, entity_type="enemy", hp=10, max_hp=10,
                 armor_class=12, position=(0, 0)):
        self.name = name
        self.entity_type = entity_type
        self.hp = hp
        self.max_hp = max_hp
        self.armor_class = armor_class
        self.position = position
        self.personality = None
        self.conditions = []
        self.stats = {"Dexterity": 10, "max_hp": max_hp}
        self.speed = 30
        self.triggers = []
        self.inventory = []


def _make_state(entities_snap, width=5, height=5):
    return GameState(
        round_number=1,
        current_entity_name=entities_snap[0].name,
        entities=tuple(entities_snap),
        initiative_order=tuple(e.name for e in entities_snap),
        world_width=width,
        world_height=height,
        tile_type="square",
    )


def _snap(name, etype, hp, max_hp, pos, alive=True):
    return EntitySnapshot(
        name=name, entity_type=etype, hp=hp, max_hp=max_hp,
        armor_class=12, position=pos, conditions=(), stats={},
        speed=30, faction=etype, is_alive=alive,
    )


# ── Tests ────────────────────────────────────────────────────────────────


class TestHeuristicAttack:
    """Entity attacks nearest enemy when in melee range."""

    def test_attacks_adjacent_enemy(self):
        goblin = SimpleEntity("Goblin", "enemy", hp=7, max_hp=7, position=(1, 0))
        fighter = SimpleEntity("Fighter", "player", hp=20, max_hp=20, position=(0, 0))

        adapter = HeuristicAIAdapter(
            entities_by_name={"Goblin": goblin, "Fighter": fighter},
            rng=random.Random(42),
        )

        state = _make_state([
            _snap("Goblin", "enemy", 7, 7, (1, 0)),
            _snap("Fighter", "player", 20, 20, (0, 0)),
        ])

        action = adapter.choose_action("Goblin", state, ["ATTACK", "MOVE", "END_TURN"])
        assert isinstance(action, AttackAction)

    def test_attacks_weakest_adjacent_enemy(self):
        goblin = SimpleEntity("Goblin", "enemy", hp=7, max_hp=7, position=(1, 1))
        fighter = SimpleEntity("Fighter", "player", hp=20, max_hp=20, position=(0, 0))
        mage = SimpleEntity("Mage", "player", hp=5, max_hp=14, position=(1, 0))

        adapter = HeuristicAIAdapter(
            entities_by_name={"Goblin": goblin, "Fighter": fighter, "Mage": mage},
            rng=random.Random(42),
        )

        state = _make_state([
            _snap("Goblin", "enemy", 7, 7, (1, 1)),
            _snap("Fighter", "player", 20, 20, (0, 0)),
            _snap("Mage", "player", 5, 14, (1, 0)),
        ])

        action = adapter.choose_action("Goblin", state, ["ATTACK", "MOVE", "END_TURN"])
        assert isinstance(action, AttackAction)
        # Should target Mage (hp=5) over Fighter (hp=20)
        assert action.target.name == "Mage"


class TestHeuristicMove:
    """Entity moves toward enemy when not adjacent."""

    def test_moves_toward_enemy(self):
        goblin = SimpleEntity("Goblin", "enemy", hp=7, max_hp=7, position=(4, 4))
        fighter = SimpleEntity("Fighter", "player", hp=20, max_hp=20, position=(0, 0))

        adapter = HeuristicAIAdapter(
            entities_by_name={"Goblin": goblin, "Fighter": fighter},
            rng=random.Random(42),
        )

        state = _make_state([
            _snap("Goblin", "enemy", 7, 7, (4, 4)),
            _snap("Fighter", "player", 20, 20, (0, 0)),
        ])

        action = adapter.choose_action("Goblin", state, ["ATTACK", "MOVE", "END_TURN"])
        assert isinstance(action, MoveAction)
        # Should move closer to (0,0) — the target position should be closer
        tx, ty = action.target_position
        assert (abs(tx - 0) + abs(ty - 0)) < (abs(4 - 0) + abs(4 - 0))


class TestHeuristicFlee:
    """Entity flees when hp_ratio < flee_threshold."""

    def test_flees_at_low_hp(self):
        # Create a personality with a high flee threshold
        cowardly = EntityPersonality(Alignment.CHAOTIC_EVIL)
        cowardly._custom_weights = TacticalWeights(flee_threshold=0.5)

        goblin = SimpleEntity("Goblin", "enemy", hp=2, max_hp=10, position=(1, 0))
        goblin.personality = cowardly
        fighter = SimpleEntity("Fighter", "player", hp=20, max_hp=20, position=(0, 0))

        adapter = HeuristicAIAdapter(
            entities_by_name={"Goblin": goblin, "Fighter": fighter},
            rng=random.Random(42),
        )

        state = _make_state([
            _snap("Goblin", "enemy", 2, 10, (1, 0)),
            _snap("Fighter", "player", 20, 20, (0, 0)),
        ])

        action = adapter.choose_action("Goblin", state, ["ATTACK", "MOVE", "END_TURN"])
        assert isinstance(action, MoveAction)
        # Should move away from Fighter at (0,0), not toward
        tx, ty = action.target_position
        assert (abs(tx - 0) + abs(ty - 0)) > (abs(1 - 0) + abs(0 - 0))

    def test_does_not_flee_at_full_hp(self):
        cowardly = EntityPersonality(Alignment.CHAOTIC_EVIL)
        cowardly._custom_weights = TacticalWeights(flee_threshold=0.3)

        goblin = SimpleEntity("Goblin", "enemy", hp=10, max_hp=10, position=(1, 0))
        goblin.personality = cowardly
        fighter = SimpleEntity("Fighter", "player", hp=20, max_hp=20, position=(0, 0))

        adapter = HeuristicAIAdapter(
            entities_by_name={"Goblin": goblin, "Fighter": fighter},
            rng=random.Random(42),
        )

        state = _make_state([
            _snap("Goblin", "enemy", 10, 10, (1, 0)),
            _snap("Fighter", "player", 20, 20, (0, 0)),
        ])

        action = adapter.choose_action("Goblin", state, ["ATTACK", "MOVE", "END_TURN"])
        # Full HP → should attack, not flee
        assert isinstance(action, AttackAction)


class TestHeuristicEndTurn:
    """Entity returns EndTurnAction when no valid actions."""

    def test_end_turn_when_only_option(self):
        goblin = SimpleEntity("Goblin", "enemy", hp=7, max_hp=7, position=(0, 0))

        adapter = HeuristicAIAdapter(
            entities_by_name={"Goblin": goblin},
            rng=random.Random(42),
        )

        state = _make_state([
            _snap("Goblin", "enemy", 7, 7, (0, 0)),
        ])

        action = adapter.choose_action("Goblin", state, ["END_TURN"])
        assert isinstance(action, EndTurnAction)

    def test_end_turn_when_no_enemies(self):
        goblin = SimpleEntity("Goblin", "enemy", hp=7, max_hp=7, position=(0, 0))

        adapter = HeuristicAIAdapter(
            entities_by_name={"Goblin": goblin},
            rng=random.Random(42),
        )

        # All enemies are dead
        state = _make_state([
            _snap("Goblin", "enemy", 7, 7, (0, 0)),
            _snap("Fighter", "player", 0, 20, (2, 2), alive=False),
        ])

        action = adapter.choose_action("Goblin", state, ["ATTACK", "MOVE", "END_TURN"])
        assert isinstance(action, EndTurnAction)


class TestHeuristicDeterminism:
    """Deterministic output with fixed seed."""

    def test_same_seed_same_result(self):
        goblin = SimpleEntity("Goblin", "enemy", hp=7, max_hp=7, position=(1, 0))
        fighter = SimpleEntity("Fighter", "player", hp=20, max_hp=20, position=(0, 0))
        entities = {"Goblin": goblin, "Fighter": fighter}

        state = _make_state([
            _snap("Goblin", "enemy", 7, 7, (1, 0)),
            _snap("Fighter", "player", 20, 20, (0, 0)),
        ])

        results = []
        for _ in range(2):
            adapter = HeuristicAIAdapter(
                entities_by_name=entities,
                rng=random.Random(42),
            )
            action = adapter.choose_action("Goblin", state, ["ATTACK", "MOVE", "END_TURN"])
            results.append(type(action).__name__)

        assert results[0] == results[1]


class TestChooseTarget:
    def test_picks_weakest(self):
        adapter = HeuristicAIAdapter(rng=random.Random(42))
        state = _make_state([
            _snap("Goblin", "enemy", 7, 7, (0, 0)),
            _snap("Fighter", "player", 20, 20, (1, 0)),
            _snap("Mage", "player", 5, 14, (2, 0)),
        ])

        target = adapter.choose_target("Goblin", state, ["Fighter", "Mage"])
        assert target == "Mage"

    def test_empty_targets(self):
        adapter = HeuristicAIAdapter(rng=random.Random(42))
        state = _make_state([_snap("Goblin", "enemy", 7, 7, (0, 0))])
        assert adapter.choose_target("Goblin", state, []) == ""


class TestPathfinderMovement:
    """Tests for pathfinder-aware multi-tile movement."""

    def _make_grid(self, width=6, height=6):
        from models.world.world_tile_manager import WorldTileManager
        return WorldTileManager(width, height, tile_type="square")

    def test_moves_multiple_tiles_with_pathfinder(self):
        """AI moves >1 tile when pathfinder + speed allow."""
        tm = self._make_grid()
        goblin = SimpleEntity("Goblin", "enemy", hp=7, max_hp=7, position=(5, 0))
        fighter = SimpleEntity("Fighter", "player", hp=20, max_hp=20, position=(0, 0))

        adapter = HeuristicAIAdapter(
            entities_by_name={"Goblin": goblin, "Fighter": fighter},
            rng=random.Random(42),
            tile_map=tm,
        )

        state = _make_state([
            _snap("Goblin", "enemy", 7, 7, (5, 0)),
            _snap("Fighter", "player", 20, 20, (0, 0)),
        ], width=6, height=6)

        action = adapter.choose_action("Goblin", state, ["ATTACK", "MOVE", "END_TURN"])
        assert isinstance(action, MoveAction)
        # Should move more than 1 tile toward Fighter
        tx, ty = action.target_position
        dist_from_start = abs(tx - 5) + abs(ty - 0)
        assert dist_from_start > 1, f"Expected multi-tile move, got {action.target_position}"

    def test_moves_around_wall_with_pathfinder(self):
        """AI routes around blocking tiles instead of getting stuck."""
        tm = self._make_grid()
        # Wall at row 0, cols 1-4 (leaving (0,0) and (5,0) open)
        for x in range(1, 5):
            tm.set_terrain_config(x, 0, blocking=True)

        goblin = SimpleEntity("Goblin", "enemy", hp=7, max_hp=7, position=(5, 0))
        fighter = SimpleEntity("Fighter", "player", hp=20, max_hp=20, position=(0, 0))

        adapter = HeuristicAIAdapter(
            entities_by_name={"Goblin": goblin, "Fighter": fighter},
            rng=random.Random(42),
            tile_map=tm,
        )

        state = _make_state([
            _snap("Goblin", "enemy", 7, 7, (5, 0)),
            _snap("Fighter", "player", 20, 20, (0, 0)),
        ], width=6, height=6)

        action = adapter.choose_action("Goblin", state, ["ATTACK", "MOVE", "END_TURN"])
        assert isinstance(action, MoveAction)
        # Must have moved (not stuck)
        assert action.target_position != (5, 0)

    def test_flee_uses_reachable_tiles(self):
        """Fleeing entity uses full speed budget to maximize distance."""
        tm = self._make_grid()
        cowardly = EntityPersonality(Alignment.CHAOTIC_EVIL)
        cowardly._custom_weights = TacticalWeights(flee_threshold=0.5)

        goblin = SimpleEntity("Goblin", "enemy", hp=2, max_hp=10, position=(1, 0))
        goblin.personality = cowardly
        fighter = SimpleEntity("Fighter", "player", hp=20, max_hp=20, position=(0, 0))

        adapter = HeuristicAIAdapter(
            entities_by_name={"Goblin": goblin, "Fighter": fighter},
            rng=random.Random(42),
            tile_map=tm,
        )

        state = _make_state([
            _snap("Goblin", "enemy", 2, 10, (1, 0)),
            _snap("Fighter", "player", 20, 20, (0, 0)),
        ], width=6, height=6)

        action = adapter.choose_action("Goblin", state, ["ATTACK", "MOVE", "END_TURN"])
        assert isinstance(action, MoveAction)
        tx, ty = action.target_position
        # Should flee far away (more than 1 tile) from Fighter at (0,0)
        flee_dist = abs(tx - 0) + abs(ty - 0)
        assert flee_dist > 2, f"Expected multi-tile flee, got {action.target_position}"

    def test_falls_back_to_simple_without_tile_map(self):
        """Without tile_map, behavior unchanged (1-tile steps)."""
        goblin = SimpleEntity("Goblin", "enemy", hp=7, max_hp=7, position=(4, 4))
        fighter = SimpleEntity("Fighter", "player", hp=20, max_hp=20, position=(0, 0))

        adapter = HeuristicAIAdapter(
            entities_by_name={"Goblin": goblin, "Fighter": fighter},
            rng=random.Random(42),
            # No tile_map
        )

        state = _make_state([
            _snap("Goblin", "enemy", 7, 7, (4, 4)),
            _snap("Fighter", "player", 20, 20, (0, 0)),
        ])

        action = adapter.choose_action("Goblin", state, ["ATTACK", "MOVE", "END_TURN"])
        assert isinstance(action, MoveAction)
        # 1-tile step: at most 1 tile away from (4,4)
        tx, ty = action.target_position
        assert max(abs(tx - 4), abs(ty - 4)) <= 1


class TestChooseMovement:
    def test_aggressive_moves_toward(self):
        aggressive = EntityPersonality(Alignment.CHAOTIC_EVIL)

        goblin = SimpleEntity("Goblin", "enemy", hp=7, max_hp=7, position=(4, 4))
        goblin.personality = aggressive

        adapter = HeuristicAIAdapter(
            entities_by_name={"Goblin": goblin},
            rng=random.Random(42),
            default_personality=aggressive,
        )

        state = _make_state([
            _snap("Goblin", "enemy", 7, 7, (4, 4)),
            _snap("Fighter", "player", 20, 20, (0, 0)),
        ])

        positions = [(3, 3), (4, 3), (3, 4)]
        chosen = adapter.choose_movement("Goblin", state, positions)
        assert chosen == (3, 3)  # Closest to Fighter at (0,0)

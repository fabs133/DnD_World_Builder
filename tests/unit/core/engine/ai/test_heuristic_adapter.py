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

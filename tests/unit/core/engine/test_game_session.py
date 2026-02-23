"""Tests for the headless GameSession orchestrator."""

import pytest
from core.engine.game_session import GameSession, GameSessionResult
from core.engine.input_adapter import TestAdapter
from core.engine.game_state import GameState
from models.game_master import Gamemaster
from models.flow.action.action import Action


class SimpleEntity:
    """Minimal entity for testing without DB/trigger deps."""

    def __init__(self, name, entity_type="player", hp=10, stats=None, speed=30):
        self.name = name
        self.entity_type = entity_type
        self.hp = hp
        self.armor_class = 12
        self.stats = stats or {"Dexterity": 10, "max_hp": hp}
        self.speed = speed
        self.conditions = []
        self.position = (0, 0)
        self.initiative = 0
        self.triggers = []
        self.inventory = []


class EndTurnAction(Action):
    """Simple pass action for testing."""

    def validate(self, game_state):
        return True

    def execute(self, game_state):
        self.execution_log.append(f"{self.actor.name} ends turn")
        return {"action": "end_turn"}


class DamageAction(Action):
    """Action that damages a target entity."""

    def __init__(self, actor, target, damage=5):
        super().__init__(actor)
        self.target = target
        self.damage = damage

    def validate(self, game_state):
        return True

    def execute(self, game_state):
        self.target.hp = max(0, self.target.hp - self.damage)
        self.execution_log.append(
            f"{self.actor.name} hits {self.target.name} for {self.damage} damage"
        )
        return {"action": "damage", "target": self.target.name, "damage": self.damage}


class TestGameSession:
    def _make_session(self, player_actions, enemy_actions, seed=42):
        gm = Gamemaster()
        player = SimpleEntity("Fighter", "player", hp=20)
        enemy = SimpleEntity("Goblin", "enemy", hp=10)
        gm.game_entities = [player, enemy]

        adapters = {
            "Fighter": TestAdapter(action_sequence=player_actions),
            "Goblin": TestAdapter(action_sequence=enemy_actions),
        }
        return GameSession(gm, adapters, seed=seed, max_rounds=10), player, enemy

    def test_basic_round(self):
        player = SimpleEntity("Fighter", "player", hp=20)
        enemy = SimpleEntity("Goblin", "enemy", hp=10)

        player_actions = [EndTurnAction(player)]
        enemy_actions = [EndTurnAction(enemy)]

        gm = Gamemaster()
        gm.game_entities = [player, enemy]

        adapters = {
            "Fighter": TestAdapter(action_sequence=player_actions),
            "Goblin": TestAdapter(action_sequence=enemy_actions),
        }
        session = GameSession(gm, adapters, seed=42, max_rounds=2)
        session.setup()

        results = session.run_one_round()
        assert len(results) == 2

    def test_combat_ends_when_enemy_dies(self):
        player = SimpleEntity("Fighter", "player", hp=20)
        enemy = SimpleEntity("Goblin", "enemy", hp=5)

        # Player kills goblin in one hit, then round ends
        player_actions = [DamageAction(player, enemy, damage=10)]
        enemy_actions = [EndTurnAction(enemy)]

        gm = Gamemaster()
        gm.game_entities = [player, enemy]

        adapters = {
            "Fighter": TestAdapter(action_sequence=player_actions),
            "Goblin": TestAdapter(action_sequence=enemy_actions),
        }
        session = GameSession(gm, adapters, seed=42, max_rounds=10)
        session.setup()

        result = session.run()
        assert result.winner == "player"
        assert "victory" in result.termination_reason

    def test_max_rounds_terminates(self):
        player = SimpleEntity("Fighter", "player", hp=20)
        enemy = SimpleEntity("Goblin", "enemy", hp=20)

        # Both just end turn forever
        player_actions = [EndTurnAction(player) for _ in range(5)]
        enemy_actions = [EndTurnAction(enemy) for _ in range(5)]

        gm = Gamemaster()
        gm.game_entities = [player, enemy]

        adapters = {
            "Fighter": TestAdapter(action_sequence=player_actions),
            "Goblin": TestAdapter(action_sequence=enemy_actions),
        }
        session = GameSession(gm, adapters, seed=42, max_rounds=3)
        session.setup()

        result = session.run()
        assert result.termination_reason == "max_rounds_reached"

    def test_get_state_returns_immutable(self):
        player = SimpleEntity("Fighter", "player", hp=20)
        gm = Gamemaster()
        gm.game_entities = [player]

        adapters = {"Fighter": TestAdapter(action_sequence=[])}
        session = GameSession(gm, adapters, seed=42)
        session.setup()

        state = session.get_state()
        assert isinstance(state, GameState)
        with pytest.raises(AttributeError):
            state.round_number = 99

    def test_deterministic_replay(self):
        """Same seed + same actions = same result."""
        def run_once(seed):
            player = SimpleEntity("Fighter", "player", hp=20)
            enemy = SimpleEntity("Goblin", "enemy", hp=5)
            player_actions = [DamageAction(player, enemy, damage=10)]
            enemy_actions = [EndTurnAction(enemy)]

            gm = Gamemaster()
            gm.game_entities = [player, enemy]

            adapters = {
                "Fighter": TestAdapter(action_sequence=player_actions),
                "Goblin": TestAdapter(action_sequence=enemy_actions),
            }
            session = GameSession(gm, adapters, seed=seed, max_rounds=10)
            session.setup()
            return session.run()

        r1 = run_once(42)
        r2 = run_once(42)
        assert r1.rounds_played == r2.rounds_played
        assert r1.winner == r2.winner
        assert r1.termination_reason == r2.termination_reason

    def test_callbacks_fire(self):
        log = []
        player = SimpleEntity("Fighter", "player", hp=20)
        enemy = SimpleEntity("Goblin", "enemy", hp=5)

        player_actions = [DamageAction(player, enemy, damage=10)]
        enemy_actions = [EndTurnAction(enemy)]

        gm = Gamemaster()
        gm.game_entities = [player, enemy]

        adapters = {
            "Fighter": TestAdapter(action_sequence=player_actions),
            "Goblin": TestAdapter(action_sequence=enemy_actions),
        }
        session = GameSession(
            gm, adapters, seed=42, max_rounds=10,
            on_round_start=lambda s: log.append("round_start"),
            on_turn_start=lambda s, n: log.append(f"turn_{n}"),
            on_action_result=lambda r: log.append(f"result_{r.success}"),
            on_round_end=lambda s: log.append("round_end"),
        )
        session.setup()
        session.run()

        assert "round_start" in log
        assert "round_end" in log
        assert any(e.startswith("turn_") for e in log)
        assert any(e.startswith("result_") for e in log)

    def test_skip_dead_entities(self):
        player = SimpleEntity("Fighter", "player", hp=20)
        enemy = SimpleEntity("Goblin", "enemy", hp=0)  # Already dead

        player_actions = [EndTurnAction(player)]

        gm = Gamemaster()
        gm.game_entities = [player, enemy]

        adapters = {
            "Fighter": TestAdapter(action_sequence=player_actions),
            "Goblin": TestAdapter(action_sequence=[]),  # Should never be called
        }
        session = GameSession(gm, adapters, seed=42, max_rounds=2)
        session.setup()
        result = session.run()

        assert result.winner == "player"

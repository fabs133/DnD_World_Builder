"""Tests for core.engine.simulation — sandbox isolation and determinism."""

from __future__ import annotations

import pytest

from core.engine.simulation import SceneSimulator, SimulationConfig


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _make_entity_dict(
    name: str,
    entity_type: str = "player",
    hp: int = 20,
    position: tuple[int, int] = (0, 0),
) -> dict:
    """Return a minimal GameEntity-compatible dict."""
    return {
        "name": name,
        "entity_type": entity_type,
        "stats": {"hp": hp, "max_hp": hp, "Dexterity": 12},
        "inventory": [],
        "triggers": [],
        "hp": hp,
        "max_hp": hp,
        "conditions": [],
        "position": list(position),
    }


def _sample_entities() -> list[dict]:
    """Two-entity encounter: one player, one enemy."""
    return [
        _make_entity_dict("Hero", "player", hp=30, position=(0, 0)),
        _make_entity_dict("Goblin", "enemy", hp=10, position=(1, 0)),
    ]


# ------------------------------------------------------------------ #
# Tests
# ------------------------------------------------------------------ #

class TestSceneSimulatorValidation:
    """Constructor guard-rails."""

    def test_no_entities_raises(self):
        with pytest.raises(ValueError, match="At least one entity"):
            SceneSimulator(entities=[])


class TestEventBusIsolation:
    """The simulator must snapshot and restore EventBus subscribers."""

    def test_context_manager_restores_eventbus(self):
        from core.gameCreation.event_bus import EventBus

        # Plant a sentinel subscriber on the live EventBus.
        sentinel_calls: list[str] = []
        sentinel = lambda data: sentinel_calls.append("called")
        EventBus.subscribe("TEST_SIM_EVENT", sentinel)

        inst = EventBus._get_instance()
        subs_before = dict(inst._subscribers)

        # Run the simulator inside a context manager.
        with SceneSimulator(_sample_entities()) as sim:
            # Inside the sandbox the sentinel should NOT be present.
            inst_inner = EventBus._get_instance()
            assert sentinel not in inst_inner._subscribers.get(
                "TEST_SIM_EVENT", []
            ), "Sentinel leaked into the sandbox"

        # After exiting, subscribers should be fully restored.
        inst_after = EventBus._get_instance()
        assert "TEST_SIM_EVENT" in inst_after._subscribers
        assert sentinel in inst_after._subscribers["TEST_SIM_EVENT"]

        # The sentinel should still work.
        EventBus.emit("TEST_SIM_EVENT", {})
        assert sentinel_calls == ["called"]

        # Cleanup: remove our sentinel so other tests aren't affected.
        EventBus.unsubscribe("TEST_SIM_EVENT", sentinel)

    def test_cleanup_always_runs(self):
        """Even if the body raises, EventBus must be restored."""
        from core.gameCreation.event_bus import EventBus

        sentinel = lambda data: None
        EventBus.subscribe("CLEANUP_TEST", sentinel)

        class _Boom(Exception):
            pass

        with pytest.raises(_Boom):
            with SceneSimulator(_sample_entities()) as sim:
                raise _Boom("intentional")

        inst = EventBus._get_instance()
        assert sentinel in inst._subscribers.get("CLEANUP_TEST", []), (
            "EventBus was not restored after exception"
        )

        EventBus.unsubscribe("CLEANUP_TEST", sentinel)


class TestDeterminism:
    """Two runs with the same seed must produce identical action logs."""

    def test_determinism(self):
        cfg = SimulationConfig(seed=99, max_rounds=5)

        with SceneSimulator(_sample_entities(), config=cfg) as sim1:
            result1 = sim1.run_to_completion()

        with SceneSimulator(_sample_entities(), config=cfg) as sim2:
            result2 = sim2.run_to_completion()

        assert result1.action_log == result2.action_log
        assert result1.rounds_played == result2.rounds_played
        assert result1.winner == result2.winner


class TestEntityIsolation:
    """Sandbox must never modify original entity dicts."""

    def test_original_hp_unchanged(self):
        entities = _sample_entities()
        original_hp = entities[1]["hp"]  # Goblin HP
        with SceneSimulator(entities) as sim:
            sim.run_to_completion()
        assert entities[1]["hp"] == original_hp

    def test_original_position_unchanged(self):
        entities = _sample_entities()
        original_pos = list(entities[0]["position"])
        with SceneSimulator(entities) as sim:
            sim.run_to_completion()
        assert entities[0]["position"] == original_pos

    def test_original_conditions_unchanged(self):
        entities = _sample_entities()
        original_conditions = list(entities[0]["conditions"])
        with SceneSimulator(entities) as sim:
            sim.run_to_completion()
        assert entities[0]["conditions"] == original_conditions


class TestConstruction:
    """Sandbox construction and entity handling."""

    def test_preserves_entity_count(self):
        entities = _sample_entities()
        with SceneSimulator(entities) as sim:
            state = sim.get_state()
            assert len(state.entities) == 2

    def test_preserves_entity_names(self):
        entities = _sample_entities()
        with SceneSimulator(entities) as sim:
            state = sim.get_state()
            names = {es.name for es in state.entities}
            assert "Hero" in names
            assert "Goblin" in names

    def test_assigns_default_positions(self):
        """Entities without positions get spread along row 0."""
        entities = [
            {"name": "A", "entity_type": "player", "stats": {"hp": 10}, "triggers": []},
            {"name": "B", "entity_type": "enemy", "stats": {"hp": 10}, "triggers": []},
        ]
        with SceneSimulator(entities) as sim:
            state = sim.get_state()
            # Should not crash — positions auto-assigned


class TestExecution:
    """Running the simulation produces results."""

    def test_run_to_completion_returns_result(self):
        with SceneSimulator(_sample_entities()) as sim:
            result = sim.run_to_completion()
            assert result.rounds_played >= 1
            assert result.winner in ("player", "enemy", None)

    def test_action_log_not_empty(self):
        with SceneSimulator(_sample_entities()) as sim:
            result = sim.run_to_completion()
            assert len(result.action_log) > 0

    def test_final_entity_states_populated(self):
        with SceneSimulator(_sample_entities()) as sim:
            result = sim.run_to_completion()
            assert len(result.final_entity_states) == 2
            for state in result.final_entity_states:
                assert "name" in state
                assert "hp" in state

    def test_run_one_round(self):
        with SceneSimulator(_sample_entities()) as sim:
            log_lines = sim.run_one_round()
            assert isinstance(log_lines, list)

    def test_reset_allows_rerun(self):
        entities = _sample_entities()
        sim = SceneSimulator(entities)
        sim.setup()
        sim.run_to_completion()
        sim.reset()
        result2 = sim.run_to_completion()
        assert result2.rounds_played >= 1
        sim.cleanup()

    def test_is_finished_after_completion(self):
        with SceneSimulator(_sample_entities()) as sim:
            sim.run_to_completion()
            assert sim.is_finished is True


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_single_player_no_enemies(self):
        """No enemies = combat should end immediately or quickly."""
        entities = [_make_entity_dict("Hero", "player", hp=30)]
        with SceneSimulator(entities) as sim:
            result = sim.run_to_completion()
            # Should complete without hanging

    def test_all_enemies_one_player(self):
        entities = [
            _make_entity_dict("Hero", "player", hp=50, position=(0, 0)),
            _make_entity_dict("G1", "enemy", hp=5, position=(1, 0)),
            _make_entity_dict("G2", "enemy", hp=5, position=(0, 1)),
            _make_entity_dict("G3", "enemy", hp=5, position=(1, 1)),
        ]
        with SceneSimulator(entities) as sim:
            result = sim.run_to_completion()
            assert result.rounds_played >= 1

    def test_max_rounds_respected(self):
        cfg = SimulationConfig(seed=42, max_rounds=2)
        entities = [
            _make_entity_dict("Hero", "player", hp=999, position=(0, 0)),
            _make_entity_dict("Boss", "enemy", hp=999, position=(1, 0)),
        ]
        with SceneSimulator(entities, config=cfg) as sim:
            result = sim.run_to_completion()
            assert result.rounds_played <= 2

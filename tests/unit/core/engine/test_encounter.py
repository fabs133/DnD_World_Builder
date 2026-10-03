"""Tests for the interactive Encounter controller."""

import pytest

from core.engine.actions.end_turn_action import EndTurnAction
from core.engine.actions.move_action import MoveAction
from core.engine.encounter import (
    DEFAULT_SPEED,
    ROUND_STARTED,
    TRIGGER_TURN_START,
    TURN_STARTED,
    Encounter,
    EncounterError,
)
from core.gameCreation.event_bus import EventBus
from models.entities.game_entity import GameEntity
from models.game_master import Gamemaster


@pytest.fixture(autouse=True)
def reset_event_bus():
    EventBus.reset()
    yield
    EventBus.reset()


@pytest.fixture
def gm():
    gm = Gamemaster()
    for name, kind, dex in (("Hero", "player", 18), ("Goblin", "enemy", 8)):
        entity = GameEntity(name, kind, stats={"hp": 10, "Dexterity": dex})
        entity.position = (0, 0)
        gm.add_entity(entity)
    return gm


def _started(gm, seed=1):
    encounter = Encounter(gm, seed=seed)
    encounter.start()
    return encounter


class TestLifecycle:

    def test_inactive_before_start(self, gm):
        encounter = Encounter(gm)
        assert not encounter.is_active
        assert encounter.current_entity_name is None
        assert encounter.order() == []

    def test_start_rolls_initiative_for_all_entities(self, gm):
        encounter = Encounter(gm, seed=1)
        order = encounter.start()
        assert {e["name"] for e in order} == {"Hero", "Goblin"}
        assert encounter.current_entity_name == order[0]["name"]
        assert encounter.round_number == 1
        assert {e["entity_type"] for e in order} == {"player", "enemy"}

    def test_same_seed_gives_same_order(self, gm):
        assert _started(gm, seed=7).order() == _started(gm, seed=7).order()

    def test_start_without_entities_raises(self):
        with pytest.raises(EncounterError):
            Encounter(Gamemaster()).start()

    def test_next_turn_wraps_into_new_round(self, gm):
        encounter = _started(gm)
        first = encounter.current_entity_name
        encounter.next_turn()
        assert encounter.current_entity_name != first
        info = encounter.next_turn()
        assert info.entity_name == first
        assert info.round_number == 2

    def test_end_clears_state(self, gm):
        encounter = _started(gm)
        encounter.end()
        assert not encounter.is_active
        assert encounter.current_entity_name is None
        with pytest.raises(EncounterError):
            encounter.next_turn()


class TestEventsAndListeners:

    def test_emits_turn_and_round_events(self, gm):
        seen = []
        for event in (TURN_STARTED, TRIGGER_TURN_START, ROUND_STARTED):
            EventBus.subscribe(event, lambda data, e=event: seen.append((e, data.get("round"))))
        encounter = _started(gm)
        encounter.next_turn()
        encounter.next_turn()  # wraps into round 2
        assert seen.count((ROUND_STARTED, 1)) == 1
        assert seen.count((ROUND_STARTED, 2)) == 1
        assert sum(1 for e, _ in seen if e == TURN_STARTED) == 3
        assert sum(1 for e, _ in seen if e == TRIGGER_TURN_START) == 3

    def test_turn_start_advances_world_turn_clock(self, gm):
        before = gm.world.turn_manager.current_turn
        encounter = _started(gm)
        encounter.next_turn()
        assert gm.world.turn_manager.current_turn == before + 2

    def test_listener_notified_on_turn_change_and_end(self, gm):
        calls = []
        encounter = Encounter(gm, seed=1)
        encounter.add_listener(calls.append)
        encounter.start()
        encounter.next_turn()
        encounter.end()
        assert [c.entity_name is not None for c in calls] == [True, True, False]

    def test_turn_start_resets_movement_budget(self, gm):
        encounter = Encounter(gm, seed=1)
        encounter.start()
        actor = encounter.current_entity
        actor.movement_remaining = 0
        encounter.next_turn()
        encounter.next_turn()
        assert actor.movement_remaining == DEFAULT_SPEED


class TestSubmit:

    def test_out_of_turn_submission_is_rejected(self, gm):
        encounter = _started(gm)
        other = next(e for e in gm.game_entities if e.name != encounter.current_entity_name)
        with pytest.raises(EncounterError):
            encounter.submit(other.name, EndTurnAction(other))

    def test_end_turn_advances(self, gm):
        encounter = _started(gm)
        actor_name = encounter.current_entity_name
        result = encounter.submit(actor_name, EndTurnAction(encounter.current_entity))
        assert result.success
        assert encounter.current_entity_name != actor_name

    def test_successful_move_keeps_turn(self, gm):
        encounter = _started(gm)
        actor = encounter.current_entity
        result = encounter.submit(actor.name, MoveAction(actor, (1, 1)))
        assert result.success
        assert actor.position == (1, 1)
        assert encounter.current_entity_name == actor.name

    def test_invalid_move_is_reported_not_executed(self, gm):
        encounter = _started(gm)
        actor = encounter.current_entity
        tile_manager = gm.world.tile_manager  # 1x1 world: (5, 5) is off the map
        result = encounter.submit(actor.name, MoveAction(actor, (5, 5), world_tile_manager=tile_manager))
        assert not result.success
        assert "Invalid tile" in result.error
        assert actor.position == (0, 0)


class _ScriptedAdapter:
    """Returns a fixed action for whoever is acting."""

    def __init__(self, make_action):
        self._make_action = make_action
        self.seen = []

    def choose_action(self, entity_name, game_state, available_actions):
        self.seen.append((entity_name, game_state.current_entity_name, tuple(available_actions)))
        return self._make_action(game_state)


class TestTakeAiTurn:

    def test_acts_then_advances_turn(self, gm):
        encounter = _started(gm)
        actor = encounter.current_entity
        adapter = _ScriptedAdapter(lambda state: MoveAction(actor, (0, 0)))

        result = encounter.take_ai_turn(adapter)

        assert result.success
        assert encounter.current_entity_name != actor.name
        name, state_name, available = adapter.seen[0]
        assert name == state_name == actor.name
        assert "MOVE" in available

    def test_end_turn_action_advances_exactly_once(self, gm):
        encounter = _started(gm)
        first = encounter.current_entity
        encounter.take_ai_turn(_ScriptedAdapter(lambda state: EndTurnAction(first)))
        assert encounter.current_entity_name != first.name
        assert encounter.round_number == 1

    def test_rejected_action_still_advances(self, gm):
        encounter = _started(gm)
        actor = encounter.current_entity
        off_map = MoveAction(actor, (9, 9), world_tile_manager=gm.world.tile_manager)

        result = encounter.take_ai_turn(_ScriptedAdapter(lambda state: off_map))

        assert not result.success
        assert encounter.current_entity_name != actor.name

    def test_heuristic_enemy_attacks_adjacent_player(self):
        from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
        from models.world.world import World

        gm = Gamemaster()
        gm.world = World(world_version=1, width=3, height=3, tile_type="square",
                         description="", map_data={}, time_of_day="", weather_conditions="")
        gm.world_tile_manager = gm.world.tile_manager
        hero = GameEntity("Hero", "player", stats={"hp": 30, "Dexterity": 1})
        goblin = GameEntity("Goblin", "enemy", stats={"hp": 7, "Dexterity": 30})
        for entity, pos in ((hero, (0, 0)), (goblin, (0, 1))):
            gm.add_entity(entity)
            gm.world_tile_manager.place_entity(entity, *pos)

        encounter = Encounter(gm, seed=3)
        encounter.start()
        assert encounter.current_entity_name == "Goblin"  # Dexterity 30 always wins initiative
        adapter = HeuristicAIAdapter(
            entities_by_name={e.name: e for e in gm.game_entities},
            world_tile_manager=gm.world_tile_manager,
        )

        result = encounter.take_ai_turn(adapter)

        assert result.success
        assert type(result.action).__name__ == "AttackAction"
        assert encounter.current_entity_name == "Hero"

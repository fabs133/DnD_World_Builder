# tests/integration/test_ambush_scenario.py
import logging
import pytest
from core.gameCreation.event_bus import EventBus
from models.world.world import World
from models.entities.game_entity import GameEntity
from core.gameCreation.trigger import Trigger
from models.flow.condition.condition_list import AlwaysTrue
from models.flow.reaction.reactions_list import AlertGamemaster

# Custom reaction: when trap activates, emit TRAP_ALERT only if not disarmed
def trap_activate_reaction(data):
    if not data.get('disarmed', False):
        EventBus.emit('TRAP_ALERT', data)

@pytest.fixture
def ambush_world():
    # 3x1 world: positions 0,1,2
    world = World(
        world_version=1,
        width=3,
        height=1,
        tile_type='square',
        description='',
        map_data={},
        time_of_day='day',
        weather_conditions='clear'
    )
    return world


def test_delayed_trap_activation_and_guard_movement(ambush_world, caplog):
    world = ambush_world
    # Create trap that always schedules activation in 2 turns
    trap = GameEntity('Spike Trap', 'trap')
    # Immediate detection and scheduling of activation
    trap.register_trigger(
        Trigger(
            'ON_ENTER',
            AlwaysTrue(),
            lambda data: world.turn_manager.schedule_in(2, trap_activate_reaction, data)
        )
    )
    world.place_entity(trap, 0, 0)

    # Two guards that will move closer in 1 turn and react on TRAP_ALERT
    guards = []
    for name, start_pos in [('Guard A', 2), ('Guard B', 2)]:
        guard = GameEntity(name, 'npc')
        guard.vision_range = 3  # enough to see trap
        guard.register_trigger(
            Trigger('TRAP_ALERT', AlwaysTrue(), AlertGamemaster(f'{name} alerted!'))
        )
        world.place_entity(guard, start_pos, 0)
        guards.append(guard)
        # Schedule each guard to move one tile toward trap at turn 1
        def make_move(g):
            def move(_):
                # move left by 1
                new_x = g.position[0] - 1
                world.place_entity(g, new_x, 0)
            return move
        world.turn_manager.schedule_in(1, make_move(guard), None)

    # Player steps on trap tile at turn 0
    with caplog.at_level(logging.DEBUG):
        data = {'position': (0, 0), 'world': world}
        EventBus.emit('ON_ENTER', data)

    # After initial emit, no alerts and guards at start_pos
    assert 'alerted!' not in caplog.text
    assert all(g.position[0] == 2 for g in guards)

    # Advance to turn 1: guards move closer
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        world.turn_manager.next_turn()
    # Guards should have moved to x=1
    assert all(g.position[0] == 1 for g in guards)

    # Advance to turn 2: trap activates and notifies guards
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        world.turn_manager.next_turn()
    assert '[GM ALERT] Guard A alerted!' in caplog.text
    assert '[GM ALERT] Guard B alerted!' in caplog.text


def test_trap_disarmed_no_activation_but_guard_sees_player(ambush_world, caplog):
    world = ambush_world
    # Create trap that disarms on detect and otherwise schedules activation
    trap = GameEntity('Spike Trap', 'trap')
    def disarm(data): data['disarmed'] = True
    # Detection trigger disarms and still schedules activation in 2 turns
    trap.register_trigger(
        Trigger('ON_ENTER', AlwaysTrue(),
                lambda data: [disarm(data), world.turn_manager.schedule_in(2, trap_activate_reaction, data)])
    )
    world.place_entity(trap, 0, 0)

    # One guard that reacts to seeing player immediately
    guard = GameEntity('Guard C', 'npc')
    guard.register_trigger(
        Trigger('ON_ENTER', lambda d: True, AlertGamemaster('Guard C saw player!'))
    )
    world.place_entity(guard, 2, 0)

    # Player steps on trap and disarms it at turn 0
    with caplog.at_level(logging.DEBUG):
        data = {'position': (0, 0), 'world': world}
        EventBus.emit('ON_ENTER', data)

    # Guard sees player immediately
    assert '[GM ALERT] Guard C saw player!' in caplog.text

    # Advance turns beyond delay: trap activation should not fire
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        world.turn_manager.next_turn()
        world.turn_manager.next_turn()
    assert 'alerted!' not in caplog.text  # no TRAP_ALERT fired

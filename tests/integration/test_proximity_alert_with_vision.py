# tests/integration/test_proximity_alert_with_vision.py
import logging
import pytest

from models.world.world import World
from core.gameCreation.event_bus import EventBus
from models.entities.game_entity import GameEntity
from core.gameCreation.trigger import Trigger
from models.flow.condition.condition_list import AlwaysTrue
from models.flow.reaction.reactions_list import AlertGamemaster
from models.tiles.tile_data import TileTag


def test_proximity_alert_within_vision_range(caplog):
    # Create a 3x1 world
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

    # 1) Place a trap at (0,0)
    trap = GameEntity('Spike Trap', 'trap')
    trap.vision_range = None
    trap.register_trigger(
        Trigger('ON_ENTER', AlwaysTrue(), AlertGamemaster('Trap sprung!'))
    )
    world.place_entity(trap, 0, 0)

    # 2) Guard A within vision (distance 1)
    guard_a = GameEntity('Guard A', 'npc')
    guard_a.vision_range = 1
    guard_a.register_trigger(
        Trigger('ON_ENTER', AlwaysTrue(), AlertGamemaster('Guard A alert!'))
    )
    world.place_entity(guard_a, 1, 0)

    # 3) Guard B out of vision (distance 2, range=1)
    guard_b = GameEntity('Guard B', 'npc')
    guard_b.vision_range = 1
    guard_b.register_trigger(
        Trigger('ON_ENTER', AlwaysTrue(), AlertGamemaster('Guard B alert!'))
    )
    world.place_entity(guard_b, 2, 0)

    # Emit event at the trap location
    with caplog.at_level(logging.DEBUG):
        EventBus.emit('ON_ENTER', {'position': (0, 0), 'world': world})

    assert '[GM ALERT] Trap sprung!' in caplog.text
    assert '[GM ALERT] Guard A alert!' in caplog.text
    assert '[GM ALERT] Guard B alert!' not in caplog.text


def test_proximity_alert_blocked_by_obstacle(caplog):
    # Create a 3x1 world
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

    # Place a trap at (0,0)
    trap = GameEntity('Spike Trap', 'trap')
    trap.vision_range = None

    trap.register_trigger(
        Trigger('ON_ENTER', AlwaysTrue(), AlertGamemaster('Trap sprung!'))
    )
    world.place_entity(trap, 0, 0)

    # Mark the tile at (1,0) as blocking vision
    world.tile_manager.tiles[(1, 0)].tags.append(TileTag.BLOCKS_VISION)

    # Guard C within nominal range but behind obstacle
    guard_c = GameEntity('Guard C', 'npc')
    guard_c.vision_range = 2
    guard_c.register_trigger(
        Trigger('ON_ENTER', AlwaysTrue(), AlertGamemaster('Guard C alert!'))
    )
    world.place_entity(guard_c, 2, 0)

    # Emit event at trap
    with caplog.at_level(logging.DEBUG):
        EventBus.emit('ON_ENTER', {'position': (0, 0), 'world': world})

    assert '[GM ALERT] Trap sprung!' in caplog.text
    assert '[GM ALERT] Guard C alert!' not in caplog.text

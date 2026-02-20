import logging
import pytest

from models.world.world import World
from core.gameCreation.event_bus import EventBus
from models.entities.game_entity import GameEntity
from core.gameCreation.trigger import Trigger
from models.flow.condition.condition_list import AlwaysTrue
from models.flow.reaction.reactions_list import AlertGamemaster

def test_multiple_entities_on_same_tile_all_react(caplog):
    # 1) Create a tiny 2×1 world
    world = World(
        world_version=1,
        width=2,
        height=1,
        tile_type='square',
        description='',
        map_data={},
        time_of_day='morning',
        weather_conditions='clear'
    )

    # 2) Make two guard entities with ON_ENTER → GM alert triggers
    guard1 = GameEntity('Guard A', 'npc')
    guard1.register_trigger(
        Trigger('ON_ENTER', AlwaysTrue(), AlertGamemaster('Guard A alert!'))
    )

    guard2 = GameEntity('Guard B', 'npc')
    guard2.register_trigger(
        Trigger('ON_ENTER', AlwaysTrue(), AlertGamemaster('Guard B alert!'))
    )

    # 3) Place both on the same tile (0,0)
    world.place_entity(guard1, 0, 0)
    world.place_entity(guard2, 0, 0)

    # 4) Fire the ON_ENTER event at (0,0)
    with caplog.at_level(logging.DEBUG):
        EventBus.emit('ON_ENTER', {'position': (0, 0), 'world': world})

    # 5) Both guards should have logged their alerts
    assert '[GM ALERT] Guard A alert!' in caplog.text
    assert '[GM ALERT] Guard B alert!' in caplog.text

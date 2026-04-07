"""Integration: EventBus events fire during headless combat actions."""

import random

import pytest

from core.events import TRIGGER_ENTER_TILE, TRIGGER_ON_DAMAGE
from core.gameCreation.event_bus import EventBus
from core.engine.actions.move_action import MoveAction
from core.engine.actions.attack_action import AttackAction
from models.world.world import World
from models.world.world_tile_manager import WorldTileManager


class SimpleEntity:
    def __init__(self, name, hp=10, position=None, entity_type="enemy"):
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.armor_class = 10
        self.position = position
        self.entity_type = entity_type
        self.speed = 30
        self.received_events = []
        self.vision_range = None

    def handle_event(self, event_type, data):
        self.received_events.append((event_type, data))


@pytest.fixture(autouse=True)
def reset_event_bus():
    """Reset EventBus between tests to prevent subscriber leaks."""
    EventBus.reset()
    yield
    EventBus.reset()


@pytest.fixture
def world():
    return World(
        world_version=1, width=5, height=5, tile_type="square",
        description="test", map_data={},
        time_of_day="day", weather_conditions="clear",
    )


class TestEnterTileEvent:

    def test_enter_tile_fires_on_move(self, world):
        """MoveAction.execute() emits ENTER_TILE when world is set.

        EventBus spatial emission notifies entities at the destination tile.
        Place an observer at the destination to verify the event.
        """
        observer = SimpleEntity("Trap", position=(2, 0), entity_type="trap")
        world.tile_manager.place_entity(observer, 2, 0)

        entity = SimpleEntity("Goblin", position=(0, 0))
        world.tile_manager.place_entity(entity, 0, 0)

        action = MoveAction(entity, (2, 0), world_tile_manager=world.tile_manager)
        action._world = world
        action.execute(None)

        # Observer at destination should have received ENTER_TILE
        enter_events = [e for e in observer.received_events if e[0] == TRIGGER_ENTER_TILE]
        assert len(enter_events) == 1
        assert enter_events[0][1]["entity"] is entity
        assert enter_events[0][1]["position"] == (2, 0)

    def test_enter_tile_not_fired_without_world(self):
        """MoveAction without _world does not emit events."""
        events = []
        EventBus.subscribe(TRIGGER_ENTER_TILE, lambda data: events.append(data))

        entity = SimpleEntity("Goblin", position=(0, 0))
        action = MoveAction(entity, (2, 0))
        # No _world set
        action.execute(None)

        assert len(events) == 0


class TestOnDamageEvent:

    def test_on_damage_fires_on_hit(self, world):
        """AttackAction.execute() emits ON_DAMAGE on a successful hit.

        The target entity at the damage position receives the event.
        """
        attacker = SimpleEntity("Fighter", hp=20, position=(0, 0))
        target = SimpleEntity("Goblin", hp=10, position=(0, 1))
        world.tile_manager.place_entity(attacker, 0, 0)
        world.tile_manager.place_entity(target, 0, 1)

        action = AttackAction(
            attacker, target,
            damage_expr="1d6", to_hit_bonus=20,
            rng=random.Random(42),
        )
        action._world = world
        result = action.execute(None)

        if result["hit"]:
            damage_events = [e for e in target.received_events if e[0] == TRIGGER_ON_DAMAGE]
            assert len(damage_events) == 1
            assert damage_events[0][1]["entity"] is attacker
            assert damage_events[0][1]["damage"] > 0

    def test_on_damage_not_fired_on_miss(self, world):
        """AttackAction does not emit ON_DAMAGE on a miss."""
        attacker = SimpleEntity("Fighter", hp=20, position=(0, 0))
        target = SimpleEntity("Dragon", hp=100, position=(0, 1))
        target.armor_class = 99
        world.tile_manager.place_entity(attacker, 0, 0)
        world.tile_manager.place_entity(target, 0, 1)

        action = AttackAction(
            attacker, target,
            damage_expr="1d6", to_hit_bonus=0,
            rng=random.Random(42),
        )
        action._world = world
        result = action.execute(None)

        if not result["hit"]:
            damage_events = [e for e in target.received_events if e[0] == TRIGGER_ON_DAMAGE]
            assert len(damage_events) == 0

    def test_on_damage_not_fired_without_world(self):
        """AttackAction without _world does not emit events."""
        events = []
        EventBus.subscribe(TRIGGER_ON_DAMAGE, lambda data: events.append(data))

        attacker = SimpleEntity("Fighter", hp=20, position=(0, 0))
        target = SimpleEntity("Goblin", hp=10, position=(0, 1))

        action = AttackAction(
            attacker, target,
            damage_expr="1d6", to_hit_bonus=20,
            rng=random.Random(42),
        )
        action.execute(None)

        assert len(events) == 0

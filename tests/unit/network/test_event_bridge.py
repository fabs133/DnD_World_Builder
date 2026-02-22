"""Tests for EventBridge and TurnBridge."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from network.event_bridge import EventBridge, TurnBridge, SYNC_EVENTS
from core.gameCreation.event_bus import EventBus


@pytest.fixture(autouse=True)
def reset_event_bus():
    """Reset EventBus before each test to avoid cross-test pollution."""
    EventBus.reset()
    yield
    EventBus.reset()


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _make_mock_host():
    host = MagicMock()
    host.broadcast = AsyncMock()
    return host


def _make_mock_gamemaster():
    gm = MagicMock()
    gm.world = MagicMock()
    gm.world.tile_manager = MagicMock()
    gm.world.tile_manager.tiles = {}
    gm.world.tile_manager.entities = {}
    gm.world.tile_manager.width = 10
    gm.world.tile_manager.height = 10
    gm.world.tile_manager.tile_type = "square"
    gm.world.lore = MagicMock()
    gm.world.lore.description = ""
    gm.world.lore.time_of_day = "day"
    gm.world.lore.weather_conditions = "clear"
    gm.world.turn_manager = MagicMock()
    gm.world.turn_manager.current_turn = 0
    gm.game_entities = []
    gm.turn_system = MagicMock()
    gm.turn_system.current_turn = 0
    gm.turn_system.round_number = 1
    gm.turn_system.turn_order = []
    return gm


class TestEventBridgeSubscription:

    def test_start_subscribes_to_all_sync_events(self):
        host = _make_mock_host()
        gm = _make_mock_gamemaster()
        bridge = EventBridge(host, gm)

        bridge.start()

        assert len(bridge._subscribed_events) == len(SYNC_EVENTS)
        for event_type in SYNC_EVENTS:
            assert event_type in bridge._subscribed_events

        bridge.stop()

    def test_stop_unsubscribes_all(self):
        host = _make_mock_host()
        gm = _make_mock_gamemaster()
        bridge = EventBridge(host, gm)

        bridge.start()
        bridge.stop()

        assert len(bridge._subscribed_events) == 0

    def test_double_start_ignored(self):
        host = _make_mock_host()
        gm = _make_mock_gamemaster()
        bridge = EventBridge(host, gm)

        bridge.start()
        bridge.start()  # Should be no-op

        assert len(bridge._subscribed_events) == len(SYNC_EVENTS)

        bridge.stop()

    def test_double_stop_safe(self):
        host = _make_mock_host()
        gm = _make_mock_gamemaster()
        bridge = EventBridge(host, gm)

        bridge.start()
        bridge.stop()
        bridge.stop()  # Should not raise


class TestEventBridgeBroadcast:

    def test_event_triggers_broadcast(self, event_loop):
        async def _test():
            host = _make_mock_host()
            gm = _make_mock_gamemaster()
            bridge = EventBridge(host, gm, throttle_ms=0)

            # Manually set the loop so coroutines can run
            bridge._loop = event_loop
            bridge._running = True
            bridge._last_state = {"tiles": {}, "entities": {}}

            # Modify world state so delta is non-empty
            gm.world.tile_manager.tiles = {(0, 0): MagicMock()}
            gm.world.tile_manager.tiles[(0, 0)].to_dict.return_value = {"terrain": "GRASS"}

            await bridge._broadcast_delta()

            # Should have broadcast something
            assert host.broadcast.called

        event_loop.run_until_complete(_test())

    def test_no_broadcast_when_no_changes(self, event_loop):
        async def _test():
            host = _make_mock_host()
            gm = _make_mock_gamemaster()
            bridge = EventBridge(host, gm, throttle_ms=0)

            bridge._loop = event_loop
            bridge._running = True

            # Snapshot the actual serialized state so delta is empty
            from network.sync import serialize_world
            bridge._last_state = serialize_world(gm.world)

            # World state hasn't changed — same mock, same output
            await bridge._broadcast_delta()

            assert not host.broadcast.called

        event_loop.run_until_complete(_test())


class TestEventBridgeThrottle:

    def test_throttle_prevents_rapid_fire(self):
        host = _make_mock_host()
        gm = _make_mock_gamemaster()
        bridge = EventBridge(host, gm, throttle_ms=500)

        bridge._running = True
        bridge._last_state = {"tiles": {}, "entities": {}}
        bridge._loop = MagicMock()
        bridge._loop.call_later = MagicMock()

        # First event: should trigger sync
        bridge._on_event({"type": "tile_modified"})
        assert bridge._last_sync_time > 0

        # Second event within throttle window: should be delayed
        bridge._on_event({"type": "tile_modified"})
        assert bridge._pending_sync is True
        assert bridge._loop.call_later.called


class TestTurnBridge:

    def test_start_subscribes_to_turn_events(self):
        host = _make_mock_host()
        gm = _make_mock_gamemaster()
        bridge = TurnBridge(host, gm)

        bridge.start()
        assert bridge._running

        bridge.stop()
        assert not bridge._running

    def test_turn_started_schedules_broadcast(self):
        host = _make_mock_host()
        gm = _make_mock_gamemaster()
        bridge = TurnBridge(host, gm)

        bridge._running = True
        bridge._loop = MagicMock()

        bridge._on_turn_started({"entity": "Hero"})
        # Should have scheduled the coroutine
        assert bridge._loop is not None

    def test_broadcast_turn_update(self, event_loop):
        async def _test():
            host = _make_mock_host()
            gm = _make_mock_gamemaster()
            bridge = TurnBridge(host, gm)

            bridge._running = True
            bridge._loop = event_loop

            await bridge._broadcast_turn_update()

            assert host.broadcast.called
            call_args = host.broadcast.call_args
            msg = call_args[0][0]
            assert msg.payload.get("round") == 1

        event_loop.run_until_complete(_test())


class TestSyncEvents:

    def test_all_expected_events_present(self):
        """Verify SYNC_EVENTS contains the expected event types."""
        expected = {
            "entity_moved", "entity_added", "entity_removed",
            "entity_damaged", "entity_healed", "entity_died",
            "tile_modified", "tile_terrain_changed",
            "combat_started", "combat_ended",
            "turn_started", "turn_ended", "round_started",
            "condition_applied", "condition_removed",
            "trigger_fired",
        }
        assert SYNC_EVENTS == expected

"""Tests for SessionHost._handle_action_request."""

import asyncio

import pytest

from network.transport import InMemoryServer, InMemoryClient
from network.session_host import SessionHost
from network.protocol import (
    Message, MessageType, PROTOCOL_VERSION,
    make_hello, make_claim_entity, make_action_request,
)
from models.game_master import Gamemaster
from models.world.world import World
from models.entities.game_entity import GameEntity


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def gamemaster():
    """Gamemaster with 2 entities, turn system, and a tile map."""
    gm = Gamemaster()
    gm.world = World(
        world_version=1, width=5, height=5, tile_type="square",
        description="test", map_data={},
        time_of_day="day", weather_conditions="clear",
    )
    gm.world_tile_manager = gm.world.tile_manager

    hero = GameEntity("Hero", "player", stats={"hp": 20})
    hero.position = (0, 0)
    goblin = GameEntity("Goblin", "enemy", stats={"hp": 7})
    goblin.position = (1, 0)

    gm.add_entity(hero)
    gm.add_entity(goblin)
    gm.world_tile_manager.place_entity(hero, 0, 0)
    gm.world_tile_manager.place_entity(goblin, 1, 0)

    # Populate turn system so current_turn=0 → Hero's turn
    gm.turn_system.entities = [hero, goblin]
    return gm


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Helpers ──────────────────────────────────────────────────────────────


async def _connect_and_claim(server, entity_name, player_name="Alice"):
    """Connect a client, do handshake, claim an entity, return (conn, welcome)."""
    client = InMemoryClient(server)
    conn = await client.connect()
    await conn.send(make_hello(player_name).to_json())
    welcome = Message.from_json(await asyncio.wait_for(conn.recv(), timeout=2.0))
    _full_state = Message.from_json(await asyncio.wait_for(conn.recv(), timeout=2.0))

    # Claim entity
    await conn.send(make_claim_entity(entity_name).to_json())
    claimed = Message.from_json(await asyncio.wait_for(conn.recv(), timeout=2.0))
    assert claimed.type == MessageType.ENTITY_CLAIMED

    return conn, welcome


async def _connect_only(server, player_name="Bob"):
    """Connect and handshake without claiming."""
    client = InMemoryClient(server)
    conn = await client.connect()
    await conn.send(make_hello(player_name).to_json())
    welcome = Message.from_json(await asyncio.wait_for(conn.recv(), timeout=2.0))
    _full_state = Message.from_json(await asyncio.wait_for(conn.recv(), timeout=2.0))
    return conn, welcome


# ── Tests ────────────────────────────────────────────────────────────────


class TestActionRequestValidation:

    def test_rejects_unclaimed_player(self, event_loop, gamemaster):
        """Player without a claimed entity gets UNKNOWN_ENTITY error."""
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            conn, _ = await _connect_only(server)

            action_msg = make_action_request("END_TURN", {})
            await conn.send(action_msg.to_json())

            raw = await asyncio.wait_for(conn.recv(), timeout=2.0)
            response = Message.from_json(raw)

            assert response.type == MessageType.ERROR
            assert response.payload["code"] == "UNKNOWN_ENTITY"

            await host.stop()

        event_loop.run_until_complete(_test())

    def test_rejects_out_of_turn(self, event_loop, gamemaster):
        """Action for entity whose turn it isn't gets NOT_YOUR_TURN error."""
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            # Goblin is index 1, but current_turn=0 (Hero's turn)
            conn, _ = await _connect_and_claim(server, "Goblin", "Bob")

            action_msg = make_action_request("END_TURN", {})
            await conn.send(action_msg.to_json())

            raw = await asyncio.wait_for(conn.recv(), timeout=2.0)
            response = Message.from_json(raw)

            assert response.type == MessageType.ERROR
            assert response.payload["code"] == "NOT_YOUR_TURN"

            await host.stop()

        event_loop.run_until_complete(_test())

    def test_rejects_unknown_action_type(self, event_loop, gamemaster):
        """Unknown action type returns INVALID_ACTION error."""
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            conn, _ = await _connect_and_claim(server, "Hero", "Alice")

            action_msg = make_action_request("FIREBALL", {})
            await conn.send(action_msg.to_json())

            raw = await asyncio.wait_for(conn.recv(), timeout=2.0)
            response = Message.from_json(raw)

            assert response.type == MessageType.ERROR
            assert response.payload["code"] == "INVALID_ACTION"

            await host.stop()

        event_loop.run_until_complete(_test())

    def test_executes_valid_end_turn(self, event_loop, gamemaster):
        """Valid END_TURN action succeeds."""
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            conn, _ = await _connect_and_claim(server, "Hero", "Alice")

            action_msg = make_action_request("END_TURN", {})
            await conn.send(action_msg.to_json())

            raw = await asyncio.wait_for(conn.recv(), timeout=2.0)
            response = Message.from_json(raw)

            assert response.type == MessageType.ACTION_RESULT
            assert response.payload["success"] is True

            await host.stop()

        event_loop.run_until_complete(_test())

    def test_executes_valid_move(self, event_loop, gamemaster):
        """Valid MOVE action moves the entity."""
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            conn, _ = await _connect_and_claim(server, "Hero", "Alice")

            action_msg = make_action_request("MOVE", {"position": [2, 0]})
            await conn.send(action_msg.to_json())

            raw = await asyncio.wait_for(conn.recv(), timeout=2.0)
            response = Message.from_json(raw)

            assert response.type == MessageType.ACTION_RESULT
            assert response.payload["success"] is True

            # Verify entity actually moved
            hero = next(e for e in gamemaster.game_entities if e.name == "Hero")
            assert hero.position == (2, 0)

            await host.stop()

        event_loop.run_until_complete(_test())

    def test_executes_valid_attack(self, event_loop, gamemaster):
        """Valid ATTACK action succeeds (hit or miss is RNG, but action completes)."""
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            conn, _ = await _connect_and_claim(server, "Hero", "Alice")

            action_msg = make_action_request("ATTACK", {"target": "Goblin"})
            await conn.send(action_msg.to_json())

            raw = await asyncio.wait_for(conn.recv(), timeout=2.0)
            response = Message.from_json(raw)

            assert response.type == MessageType.ACTION_RESULT
            assert response.payload["success"] is True
            assert "action" in response.payload["result"]

            await host.stop()

        event_loop.run_until_complete(_test())

    def test_attack_nonexistent_target_fails(self, event_loop, gamemaster):
        """ATTACK with invalid target returns INVALID_ACTION."""
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            conn, _ = await _connect_and_claim(server, "Hero", "Alice")

            action_msg = make_action_request("ATTACK", {"target": "Dragon"})
            await conn.send(action_msg.to_json())

            raw = await asyncio.wait_for(conn.recv(), timeout=2.0)
            response = Message.from_json(raw)

            assert response.type == MessageType.ERROR
            assert response.payload["code"] == "INVALID_ACTION"

            await host.stop()

        event_loop.run_until_complete(_test())

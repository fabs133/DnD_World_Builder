"""Integration test: full player action flow over in-memory transport."""

import asyncio

import pytest

from network.transport import InMemoryServer, InMemoryClient
from network.session_host import SessionHost
from network.protocol import (
    Message, MessageType,
    make_hello, make_claim_entity, make_action_request,
)
from models.game_master import Gamemaster
from models.world.world import World
from models.entities.game_entity import GameEntity


@pytest.fixture
def gamemaster():
    gm = Gamemaster()
    gm.world = World(
        world_version=1, width=5, height=5, tile_type="square",
        description="test arena", map_data={},
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


async def _connect_and_claim(server, entity_name, player_name):
    """Connect, handshake, claim entity."""
    client = InMemoryClient(server)
    conn = await client.connect()
    await conn.send(make_hello(player_name).to_json())
    welcome = Message.from_json(await asyncio.wait_for(conn.recv(), timeout=2.0))
    _full_state = Message.from_json(await asyncio.wait_for(conn.recv(), timeout=2.0))
    await conn.send(make_claim_entity(entity_name).to_json())
    claimed = Message.from_json(await asyncio.wait_for(conn.recv(), timeout=2.0))
    assert claimed.type == MessageType.ENTITY_CLAIMED
    return conn, welcome


class TestNetworkedActions:

    def test_full_move_flow(self, event_loop, gamemaster):
        """Connect → claim → move → verify position changes on both sides."""
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            conn, _ = await _connect_and_claim(server, "Hero", "Alice")

            # Send MOVE action
            move_msg = make_action_request("MOVE", {"position": [3, 0]})
            await conn.send(move_msg.to_json())

            # Should get ACTION_RESULT(success=True)
            raw = await asyncio.wait_for(conn.recv(), timeout=2.0)
            result = Message.from_json(raw)
            assert result.type == MessageType.ACTION_RESULT
            assert result.payload["success"] is True

            # Entity position should be updated in the gamemaster
            hero = next(e for e in gamemaster.game_entities if e.name == "Hero")
            assert hero.position == (3, 0)

            await host.stop()

        event_loop.run_until_complete(_test())

    def test_two_players_sequential_turns(self, event_loop, gamemaster):
        """Player 1 acts on their turn, player 2 gets rejected until their turn."""
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            # Alice claims Hero (turn 0)
            conn_alice, _ = await _connect_and_claim(server, "Hero", "Alice")
            # Bob claims Goblin (turn 1)
            conn_bob, _ = await _connect_and_claim(server, "Goblin", "Bob")

            # Both players may have pending ENTITY_CLAIMED broadcasts — drain them
            for conn in (conn_alice, conn_bob):
                try:
                    await asyncio.wait_for(conn.recv(), timeout=0.2)
                except (asyncio.TimeoutError, ConnectionError, asyncio.CancelledError):
                    pass

            # Bob tries to act (Goblin) — should be rejected (it's Hero's turn)
            action_msg = make_action_request("END_TURN", {})
            await conn_bob.send(action_msg.to_json())

            raw = await asyncio.wait_for(conn_bob.recv(), timeout=2.0)
            bob_result = Message.from_json(raw)
            assert bob_result.type == MessageType.ERROR
            assert bob_result.payload["code"] == "NOT_YOUR_TURN"

            # Alice acts (Hero) — should succeed
            await conn_alice.send(action_msg.to_json())
            raw = await asyncio.wait_for(conn_alice.recv(), timeout=2.0)
            alice_result = Message.from_json(raw)
            assert alice_result.type == MessageType.ACTION_RESULT
            assert alice_result.payload["success"] is True

            await host.stop()

        event_loop.run_until_complete(_test())

    def test_action_result_contains_result_data(self, event_loop, gamemaster):
        """ACTION_RESULT for a move contains from/to positions."""
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            conn, _ = await _connect_and_claim(server, "Hero", "Alice")

            move_msg = make_action_request("MOVE", {"position": [2, 2]})
            await conn.send(move_msg.to_json())

            raw = await asyncio.wait_for(conn.recv(), timeout=2.0)
            result = Message.from_json(raw)

            assert result.type == MessageType.ACTION_RESULT
            assert result.payload["success"] is True
            assert result.payload["result"]["action"] == "move"
            assert result.payload["result"]["to"] == (2, 2) or result.payload["result"]["to"] == [2, 2]

            await host.stop()

        event_loop.run_until_complete(_test())

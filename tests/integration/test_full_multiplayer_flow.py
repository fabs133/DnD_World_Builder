"""Integration test: full multiplayer flow including action requests."""

import asyncio

import pytest

from network.transport import InMemoryServer, InMemoryClient
from network.session_host import SessionHost
from network.session_client import SessionClient
from network.protocol import MessageType, make_action_request
from models.game_master import Gamemaster
from models.world.world import World
from models.entities.game_entity import GameEntity


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def gamemaster():
    """Gamemaster with 2 entities and turn system for action tests."""
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

    # Hero goes first
    gm.turn_system.entities = [hero, goblin]
    return gm


async def _make_session(gamemaster):
    server = InMemoryServer()
    host = SessionHost(gamemaster, server)
    await host.start()
    return host, server


async def _connect_player(server, name):
    client = SessionClient(name, InMemoryClient(server))
    await client.connect()
    listen_task = asyncio.ensure_future(client.listen())
    await asyncio.sleep(0.05)
    return client, listen_task


class TestFullMultiplayerFlow:

    def test_join_claim_action_disconnect(self, event_loop, gamemaster):
        """Full flow: join session, claim entity, execute action, disconnect."""

        async def _test():
            host, server = await _make_session(gamemaster)

            # Player connects and claims Hero
            client, listen_task = await _connect_player(server, "Alice")
            assert client.session_id is not None
            assert len(client.available_entities) == 2

            await client.claim_entity("Hero")
            await asyncio.sleep(0.05)
            assert client.claimed_entity_id == "Hero"

            # Player sends END_TURN action
            action_results = []
            client.on(
                MessageType.ACTION_RESULT,
                lambda msg: action_results.append(msg.payload),
            )

            await client.request_action("END_TURN", {})
            await asyncio.sleep(0.1)

            assert len(action_results) == 1
            assert action_results[0]["success"] is True
            assert action_results[0]["result"]["action"] == "end_turn"

            # Disconnect
            await client.disconnect()
            listen_task.cancel()
            await host.stop()

        event_loop.run_until_complete(_test())

    def test_action_rejected_not_your_turn(self, event_loop, gamemaster):
        """Action is rejected if it is not the requesting entity's turn."""

        async def _test():
            host, server = await _make_session(gamemaster)

            # Player 1 claims Hero (turn 0 = Hero's turn)
            client1, task1 = await _connect_player(server, "Alice")
            await client1.claim_entity("Hero")
            await asyncio.sleep(0.05)

            # Player 2 claims Goblin
            client2, task2 = await _connect_player(server, "Bob")
            await client2.claim_entity("Goblin")
            await asyncio.sleep(0.05)

            # Bob tries to act on Goblin's behalf — should be rejected
            errors = []
            client2.on(
                MessageType.ERROR,
                lambda msg: errors.append(msg.payload),
            )

            await client2.request_action("END_TURN", {})
            await asyncio.sleep(0.1)

            assert len(errors) == 1
            assert "turn" in errors[0].get("message", "").lower()

            # Cleanup
            await client1.disconnect()
            await client2.disconnect()
            task1.cancel()
            task2.cancel()
            await host.stop()

        event_loop.run_until_complete(_test())

    def test_chat_relay(self, event_loop, gamemaster):
        """Chat messages are relayed to all clients."""

        async def _test():
            host, server = await _make_session(gamemaster)

            client1, task1 = await _connect_player(server, "Alice")
            client2, task2 = await _connect_player(server, "Bob")

            chat_messages = []
            client2.on(
                MessageType.CHAT,
                lambda msg: chat_messages.append(msg.payload),
            )

            await client1.send_chat("Hello everyone!")
            await asyncio.sleep(0.1)

            assert len(chat_messages) == 1
            assert chat_messages[0]["message"] == "Hello everyone!"

            await client1.disconnect()
            await client2.disconnect()
            task1.cancel()
            task2.cancel()
            await host.stop()

        event_loop.run_until_complete(_test())

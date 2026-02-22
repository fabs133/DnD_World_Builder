import asyncio
import pytest
from network.transport import InMemoryServer, InMemoryClient
from network.session_host import SessionHost
from network.protocol import (
    Message, MessageType, PROTOCOL_VERSION,
    make_hello, make_claim_entity, make_chat,
)
from models.game_master import Gamemaster
from models.entities.game_entity import GameEntity


@pytest.fixture
def gamemaster():
    gm = Gamemaster()
    gm.add_entity(GameEntity("Hero", "player", stats={"hp": 20}))
    gm.add_entity(GameEntity("Goblin", "enemy", stats={"hp": 5}))
    return gm


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def _connect_client(server, player_name="Alice"):
    """Helper: connect a client, do handshake, return (conn, welcome_msg, full_state_msg)."""
    client = InMemoryClient(server)
    conn = await client.connect()
    await conn.send(make_hello(player_name).to_json())
    welcome = Message.from_json(await asyncio.wait_for(conn.recv(), timeout=2.0))
    full_state = Message.from_json(await asyncio.wait_for(conn.recv(), timeout=2.0))
    return conn, welcome, full_state


class TestHandshake:

    def test_hello_welcome_flow(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            conn, welcome, full_state = await _connect_client(server)

            assert welcome.type == MessageType.WELCOME
            assert welcome.payload["session_id"] == host.session_id
            assert "player_id" in welcome.payload
            assert len(welcome.payload["entities"]) == 2

            assert full_state.type == MessageType.FULL_STATE
            assert "world" in full_state.payload
            assert "entities" in full_state.payload
            assert "turn" in full_state.payload

            await host.stop()

        event_loop.run_until_complete(_test())

    def test_version_mismatch_rejected(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            client = InMemoryClient(server)
            conn = await client.connect()

            bad_hello = Message(
                type=MessageType.HELLO,
                payload={"player_name": "Bob", "version": "0.0"},
            )
            await conn.send(bad_hello.to_json())

            raw = await asyncio.wait_for(conn.recv(), timeout=2.0)
            response = Message.from_json(raw)
            assert response.type == MessageType.ERROR
            assert response.payload["code"] == "VERSION_MISMATCH"

            await host.stop()

        event_loop.run_until_complete(_test())

    def test_non_hello_first_message_rejected(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            client = InMemoryClient(server)
            conn = await client.connect()

            await conn.send(make_chat("x", "hi").to_json())

            raw = await asyncio.wait_for(conn.recv(), timeout=2.0)
            response = Message.from_json(raw)
            assert response.type == MessageType.ERROR
            assert response.payload["code"] == "INVALID_MESSAGE"

            await host.stop()

        event_loop.run_until_complete(_test())

    def test_welcome_includes_entity_list(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            conn, welcome, _ = await _connect_client(server)

            entity_names = [e["name"] for e in welcome.payload["entities"]]
            assert "Hero" in entity_names
            assert "Goblin" in entity_names

            await host.stop()

        event_loop.run_until_complete(_test())


class TestEntityClaiming:

    def test_claim_entity_success(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            conn, welcome, _ = await _connect_client(server)
            listen_task = asyncio.ensure_future(self._drain(conn))

            await conn.send(make_claim_entity("Hero").to_json())
            raw = await asyncio.wait_for(conn.recv(), timeout=2.0)
            claimed = Message.from_json(raw)

            assert claimed.type == MessageType.ENTITY_CLAIMED
            assert claimed.payload["entity_id"] == "Hero"
            assert claimed.payload["player_id"] == welcome.payload["player_id"]

            listen_task.cancel()
            await host.stop()

        event_loop.run_until_complete(_test())

    def test_claim_nonexistent_entity(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            conn, _, _ = await _connect_client(server)

            await conn.send(make_claim_entity("Dragon").to_json())
            raw = await asyncio.wait_for(conn.recv(), timeout=2.0)
            error = Message.from_json(raw)

            assert error.type == MessageType.ERROR
            assert error.payload["code"] == "UNKNOWN_ENTITY"

            await host.stop()

        event_loop.run_until_complete(_test())

    def test_claim_already_claimed_entity(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            # Player 1 claims Hero
            conn1, _, _ = await _connect_client(server, "Alice")
            await conn1.send(make_claim_entity("Hero").to_json())
            await asyncio.wait_for(conn1.recv(), timeout=2.0)  # ENTITY_CLAIMED

            # Player 2 tries to claim Hero
            conn2, _, _ = await _connect_client(server, "Bob")
            await conn2.send(make_claim_entity("Hero").to_json())

            # Player 2 may first receive the ENTITY_CLAIMED broadcast from Player 1
            # Then gets their own error, so read until we get ERROR
            for _ in range(3):
                raw = await asyncio.wait_for(conn2.recv(), timeout=2.0)
                msg = Message.from_json(raw)
                if msg.type == MessageType.ERROR:
                    break

            assert msg.type == MessageType.ERROR
            assert msg.payload["code"] == "ENTITY_ALREADY_CLAIMED"

            await host.stop()

        event_loop.run_until_complete(_test())

    @staticmethod
    async def _drain(conn):
        """Drain messages to prevent queue backup."""
        try:
            while True:
                await conn.recv()
        except (ConnectionError, asyncio.CancelledError):
            pass


class TestChat:

    def test_chat_broadcast_to_all_players(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            conn1, _, _ = await _connect_client(server, "Alice")
            conn2, _, _ = await _connect_client(server, "Bob")

            await conn1.send(make_chat("Alice", "Hello everyone!").to_json())
            await asyncio.sleep(0.05)

            # Both players should receive the chat (host broadcasts to all)
            raw1 = await asyncio.wait_for(conn1.recv(), timeout=2.0)
            chat1 = Message.from_json(raw1)
            assert chat1.type == MessageType.CHAT
            assert chat1.payload["message"] == "Hello everyone!"

            raw2 = await asyncio.wait_for(conn2.recv(), timeout=2.0)
            chat2 = Message.from_json(raw2)
            assert chat2.type == MessageType.CHAT
            assert chat2.payload["message"] == "Hello everyone!"

            await host.stop()

        event_loop.run_until_complete(_test())


class TestPlayerTracking:

    def test_player_added_on_connect(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            assert len(host.players) == 0
            await _connect_client(server, "Alice")
            await asyncio.sleep(0.01)
            assert len(host.players) == 1

            await _connect_client(server, "Bob")
            await asyncio.sleep(0.01)
            assert len(host.players) == 2

            await host.stop()

        event_loop.run_until_complete(_test())

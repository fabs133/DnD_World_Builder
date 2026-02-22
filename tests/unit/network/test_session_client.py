import asyncio
import pytest
from network.transport import InMemoryServer, InMemoryClient
from network.session_host import SessionHost
from network.session_client import SessionClient
from network.protocol import Message, MessageType
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


class TestConnect:

    def test_connect_populates_fields(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            client = SessionClient("Alice", InMemoryClient(server))
            await client.connect()

            assert client.session_id == host.session_id
            assert client.player_id is not None
            assert len(client.available_entities) == 2

            entity_names = [e["name"] for e in client.available_entities]
            assert "Hero" in entity_names
            assert "Goblin" in entity_names

            await host.stop()

        event_loop.run_until_complete(_test())

    def test_connect_version_mismatch_raises(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            # Monkey-patch the protocol version for this client
            import network.protocol as proto
            original = proto.PROTOCOL_VERSION
            proto.PROTOCOL_VERSION = "0.0"
            try:
                client = SessionClient("Bob", InMemoryClient(server))
                with pytest.raises(ConnectionError, match="Server rejected"):
                    await client.connect()
            finally:
                proto.PROTOCOL_VERSION = original

            await host.stop()

        event_loop.run_until_complete(_test())


class TestListen:

    def test_full_state_updates_world_state(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            client = SessionClient("Alice", InMemoryClient(server))
            await client.connect()

            assert client.world_state is None
            listen_task = asyncio.ensure_future(client.listen())
            await asyncio.sleep(0.05)

            assert client.world_state is not None
            assert "tiles" in client.world_state
            assert client.turn_state is not None

            listen_task.cancel()
            await host.stop()

        event_loop.run_until_complete(_test())

    def test_entity_claimed_updates_client(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            client = SessionClient("Alice", InMemoryClient(server))
            await client.connect()
            listen_task = asyncio.ensure_future(client.listen())
            await asyncio.sleep(0.05)

            assert client.claimed_entity_id is None
            await client.claim_entity("Hero")
            await asyncio.sleep(0.05)
            assert client.claimed_entity_id == "Hero"

            listen_task.cancel()
            await host.stop()

        event_loop.run_until_complete(_test())

    def test_handler_callbacks_fire(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            client = SessionClient("Alice", InMemoryClient(server))
            await client.connect()

            received = []
            client.on(MessageType.FULL_STATE, lambda m: received.append(m))
            listen_task = asyncio.ensure_future(client.listen())
            await asyncio.sleep(0.05)

            assert len(received) == 1
            assert received[0].type == MessageType.FULL_STATE

            listen_task.cancel()
            await host.stop()

        event_loop.run_until_complete(_test())

    def test_chat_handler_fires(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            client1 = SessionClient("Alice", InMemoryClient(server))
            await client1.connect()
            listen1 = asyncio.ensure_future(client1.listen())

            client2 = SessionClient("Bob", InMemoryClient(server))
            await client2.connect()

            chat_received = []
            client2.on(MessageType.CHAT, lambda m: chat_received.append(m))
            listen2 = asyncio.ensure_future(client2.listen())
            await asyncio.sleep(0.05)

            await client1.send_chat("Hello Bob!")
            await asyncio.sleep(0.05)

            assert len(chat_received) >= 1
            assert chat_received[0].payload["message"] == "Hello Bob!"

            listen1.cancel()
            listen2.cancel()
            await host.stop()

        event_loop.run_until_complete(_test())


class TestSendMethods:

    def test_claim_entity_sends_message(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            client = SessionClient("Alice", InMemoryClient(server))
            await client.connect()
            listen_task = asyncio.ensure_future(client.listen())
            await asyncio.sleep(0.05)

            await client.claim_entity("Hero")
            await asyncio.sleep(0.05)
            assert client.claimed_entity_id == "Hero"

            listen_task.cancel()
            await host.stop()

        event_loop.run_until_complete(_test())

    def test_disconnect(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            client = SessionClient("Alice", InMemoryClient(server))
            await client.connect()

            assert not client.conn.closed
            await client.disconnect()
            assert client.conn.closed

            await host.stop()

        event_loop.run_until_complete(_test())

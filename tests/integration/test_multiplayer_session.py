"""Integration tests: full host + multiple clients in a single process, no sockets."""
import asyncio
import pytest
from network.transport import InMemoryServer, InMemoryClient
from network.session_host import SessionHost
from network.session_client import SessionClient
from network.protocol import MessageType
from models.game_master import Gamemaster
from models.entities.game_entity import GameEntity


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def gamemaster():
    gm = Gamemaster()
    gm.add_entity(GameEntity("Hero", "player", stats={"hp": 20}))
    gm.add_entity(GameEntity("Rogue", "player", stats={"hp": 15}))
    gm.add_entity(GameEntity("Goblin", "enemy", stats={"hp": 5}))
    return gm


async def _make_session(gamemaster):
    """Create and start a session host, return (host, server)."""
    server = InMemoryServer()
    host = SessionHost(gamemaster, server)
    await host.start()
    return host, server


async def _connect_player(server, name):
    """Connect a SessionClient, start listening, return client + listen task."""
    client = SessionClient(name, InMemoryClient(server))
    await client.connect()
    listen_task = asyncio.ensure_future(client.listen())
    await asyncio.sleep(0.05)
    return client, listen_task


class TestTwoPlayerSession:

    def test_two_players_connect_and_see_entities(self, event_loop, gamemaster):
        async def _test():
            host, server = await _make_session(gamemaster)

            alice, t1 = await _connect_player(server, "Alice")
            bob, t2 = await _connect_player(server, "Bob")

            # Both players should be in the same session
            assert alice.session_id == bob.session_id

            # Both should see all 3 entities
            assert len(alice.available_entities) == 3
            assert len(bob.available_entities) == 3

            # Both should have world state from FULL_STATE
            assert alice.world_state is not None
            assert bob.world_state is not None

            t1.cancel()
            t2.cancel()
            await host.stop()

        event_loop.run_until_complete(_test())

    def test_two_players_claim_different_entities(self, event_loop, gamemaster):
        async def _test():
            host, server = await _make_session(gamemaster)

            alice, t1 = await _connect_player(server, "Alice")
            bob, t2 = await _connect_player(server, "Bob")

            await alice.claim_entity("Hero")
            await asyncio.sleep(0.05)
            assert alice.claimed_entity_id == "Hero"

            await bob.claim_entity("Rogue")
            await asyncio.sleep(0.05)
            assert bob.claimed_entity_id == "Rogue"

            # Verify host tracked the claims
            assert "Hero" in host._entity_claims
            assert "Rogue" in host._entity_claims

            t1.cancel()
            t2.cancel()
            await host.stop()

        event_loop.run_until_complete(_test())

    def test_duplicate_entity_claim_rejected(self, event_loop, gamemaster):
        async def _test():
            host, server = await _make_session(gamemaster)

            alice, t1 = await _connect_player(server, "Alice")
            bob, t2 = await _connect_player(server, "Bob")

            # Alice claims Hero
            await alice.claim_entity("Hero")
            await asyncio.sleep(0.05)
            assert alice.claimed_entity_id == "Hero"

            # Bob tries to claim Hero (should fail)
            errors = []
            bob.on(MessageType.ERROR, lambda m: errors.append(m))

            await bob.claim_entity("Hero")
            await asyncio.sleep(0.05)

            assert bob.claimed_entity_id is None
            assert len(errors) >= 1
            assert errors[0].payload["code"] == "ENTITY_ALREADY_CLAIMED"

            t1.cancel()
            t2.cancel()
            await host.stop()

        event_loop.run_until_complete(_test())


class TestChatBroadcast:

    def test_chat_from_one_player_received_by_other(self, event_loop, gamemaster):
        async def _test():
            host, server = await _make_session(gamemaster)

            alice, t1 = await _connect_player(server, "Alice")

            bob_chats = []
            bob, t2 = await _connect_player(server, "Bob")
            bob.on(MessageType.CHAT, lambda m: bob_chats.append(m))

            await alice.send_chat("Roll for initiative!")
            await asyncio.sleep(0.05)

            assert len(bob_chats) >= 1
            assert bob_chats[0].payload["message"] == "Roll for initiative!"
            assert bob_chats[0].payload["sender"] == "Alice"

            t1.cancel()
            t2.cancel()
            await host.stop()

        event_loop.run_until_complete(_test())

    def test_multiple_chat_messages(self, event_loop, gamemaster):
        async def _test():
            host, server = await _make_session(gamemaster)

            alice, t1 = await _connect_player(server, "Alice")

            bob_chats = []
            bob, t2 = await _connect_player(server, "Bob")
            bob.on(MessageType.CHAT, lambda m: bob_chats.append(m))

            await alice.send_chat("Message 1")
            await alice.send_chat("Message 2")
            await bob.send_chat("Reply")
            await asyncio.sleep(0.1)

            messages = [m.payload["message"] for m in bob_chats]
            assert "Message 1" in messages
            assert "Message 2" in messages
            # Bob also gets his own chat back (broadcast to all)
            assert "Reply" in messages

            t1.cancel()
            t2.cancel()
            await host.stop()

        event_loop.run_until_complete(_test())


class TestDisconnect:

    def test_disconnect_removes_player(self, event_loop, gamemaster):
        async def _test():
            host, server = await _make_session(gamemaster)

            alice, t1 = await _connect_player(server, "Alice")
            bob, t2 = await _connect_player(server, "Bob")

            assert len(host.players) == 2

            await alice.disconnect()
            t1.cancel()
            await asyncio.sleep(0.1)

            # Alice should be removed from host's player list
            assert len(host.players) == 1

            t2.cancel()
            await host.stop()

        event_loop.run_until_complete(_test())


class TestThreePlayerSession:

    def test_three_players_full_flow(self, event_loop, gamemaster):
        """End-to-end: 3 players connect, claim entities, chat."""
        async def _test():
            host, server = await _make_session(gamemaster)

            alice, t1 = await _connect_player(server, "Alice")
            bob, t2 = await _connect_player(server, "Bob")
            charlie, t3 = await _connect_player(server, "Charlie")

            assert len(host.players) == 3

            # Each claims a different entity
            await alice.claim_entity("Hero")
            await bob.claim_entity("Rogue")
            await charlie.claim_entity("Goblin")
            await asyncio.sleep(0.1)

            assert alice.claimed_entity_id == "Hero"
            assert bob.claimed_entity_id == "Rogue"
            assert charlie.claimed_entity_id == "Goblin"

            # Chat
            charlie_chats = []
            charlie.on(MessageType.CHAT, lambda m: charlie_chats.append(m))

            await alice.send_chat("Let's go!")
            await asyncio.sleep(0.05)

            assert any(m.payload["message"] == "Let's go!" for m in charlie_chats)

            t1.cancel()
            t2.cancel()
            t3.cancel()
            await host.stop()

        event_loop.run_until_complete(_test())

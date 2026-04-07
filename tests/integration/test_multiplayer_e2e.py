"""End-to-end multiplayer integration test.

Spawns one host and two clients using InMemoryTransport (no real sockets).
Exercises the complete lobby → gameplay → disconnect lifecycle:
  - Connection & handshake
  - Entity claiming (success, duplicate, nonexistent)
  - Turn-based actions (END_TURN, MOVE, ATTACK)
  - Turn validation (wrong-turn rejection)
  - Chat relay
  - State consistency
  - Graceful disconnect

Run with: ``pytest -m slow tests/integration/test_multiplayer_e2e.py -v``
"""

from __future__ import annotations

import asyncio

import pytest

from network.transport import InMemoryServer, InMemoryClient
from network.session_host import SessionHost
from network.session_client import SessionClient
from network.protocol import MessageType, ErrorCode
from models.game_master import Gamemaster
from models.world.world import World
from models.entities.game_entity import GameEntity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_gamemaster() -> Gamemaster:
    """3 entities on a 5x5 grid with turn order set."""
    gm = Gamemaster()
    gm.world = World(
        world_version=1, width=5, height=5, tile_type="square",
        description="E2E test world", map_data={},
        time_of_day="day", weather_conditions="clear",
    )
    gm.world_tile_manager = gm.world.tile_manager

    paladin = GameEntity("Paladin", "player",
                         stats={"hp": 25, "max_hp": 25, "armor_class": 16, "speed": 30})
    paladin.position = (0, 0)

    ranger = GameEntity("Ranger", "player",
                        stats={"hp": 20, "max_hp": 20, "armor_class": 14, "speed": 30})
    ranger.position = (1, 0)

    goblin = GameEntity("Goblin", "enemy",
                        stats={"hp": 7, "max_hp": 7, "armor_class": 13, "speed": 30})
    goblin.position = (4, 4)

    for e in (paladin, ranger, goblin):
        gm.add_entity(e)
        gm.world_tile_manager.place_entity(e, *e.position)

    gm.turn_system.entities = [paladin, ranger, goblin]
    return gm


async def _setup(gm: Gamemaster):
    """Create InMemory server + SessionHost and start it."""
    server = InMemoryServer()
    host = SessionHost(gm, server)
    await host.start()
    return server, host


async def _connect(server: InMemoryServer, name: str):
    """Connect a client, start its listen loop, return (client, listen_task)."""
    client = SessionClient(name, InMemoryClient(server))
    await client.connect()
    task = asyncio.ensure_future(client.listen())
    await asyncio.sleep(0.05)  # let FULL_STATE arrive
    return client, task


async def _cleanup(host: SessionHost, *tasks: asyncio.Task):
    for t in tasks:
        t.cancel()
    await host.stop()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def gamemaster():
    return _build_gamemaster()


# ---------------------------------------------------------------------------
# Phase 1 — Connection & Lobby
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestConnectionAndLobby:

    def test_host_starts_and_accepts_connections(self, event_loop, gamemaster):
        """Two clients connect and both receive WELCOME with entity list."""
        async def _test():
            server, host = await _setup(gamemaster)
            alice, t1 = await _connect(server, "Alice")
            bob, t2 = await _connect(server, "Bob")

            # Both got a session id and entity list
            assert alice.session_id is not None
            assert bob.session_id == alice.session_id
            assert len(alice.available_entities) == 3
            assert len(bob.available_entities) == 3

            # Host tracks both players
            assert len(host.players) == 2

            await _cleanup(host, t1, t2)

        event_loop.run_until_complete(_test())

    def test_clients_receive_full_state_on_connect(self, event_loop, gamemaster):
        """Both clients have world_state populated after connect + listen."""
        async def _test():
            server, host = await _setup(gamemaster)
            alice, t1 = await _connect(server, "Alice")
            bob, t2 = await _connect(server, "Bob")

            assert alice.world_state is not None
            assert bob.world_state is not None
            # World state should contain tiles
            assert "tiles" in alice.world_state
            assert "entities" in alice.world_state

            await _cleanup(host, t1, t2)

        event_loop.run_until_complete(_test())

    def test_entity_claiming(self, event_loop, gamemaster):
        """Alice claims Paladin, Bob claims Ranger — both confirmed."""
        async def _test():
            server, host = await _setup(gamemaster)
            alice, t1 = await _connect(server, "Alice")
            bob, t2 = await _connect(server, "Bob")

            await alice.claim_entity("Paladin")
            await asyncio.sleep(0.05)
            assert alice.claimed_entity_id == "Paladin"

            await bob.claim_entity("Ranger")
            await asyncio.sleep(0.05)
            assert bob.claimed_entity_id == "Ranger"

            # Host tracks claims
            assert host._entity_claims["Paladin"] == alice.player_id
            assert host._entity_claims["Ranger"] == bob.player_id

            await _cleanup(host, t1, t2)

        event_loop.run_until_complete(_test())

    def test_duplicate_claim_rejected(self, event_loop, gamemaster):
        """Bob cannot claim Paladin after Alice already claimed it."""
        async def _test():
            server, host = await _setup(gamemaster)
            alice, t1 = await _connect(server, "Alice")
            bob, t2 = await _connect(server, "Bob")

            await alice.claim_entity("Paladin")
            await asyncio.sleep(0.05)

            # Bob tries to claim same entity
            errors = []
            bob.on(MessageType.ERROR, lambda msg: errors.append(msg.payload))
            await bob.claim_entity("Paladin")
            await asyncio.sleep(0.05)

            assert len(errors) >= 1
            assert "ENTITY_ALREADY_CLAIMED" in str(errors[0].get("code", ""))
            assert bob.claimed_entity_id is None  # Not claimed

            await _cleanup(host, t1, t2)

        event_loop.run_until_complete(_test())

    def test_nonexistent_entity_claim_rejected(self, event_loop, gamemaster):
        """Claiming a nonexistent entity returns UNKNOWN_ENTITY error."""
        async def _test():
            server, host = await _setup(gamemaster)
            alice, t1 = await _connect(server, "Alice")

            errors = []
            alice.on(MessageType.ERROR, lambda msg: errors.append(msg.payload))
            await alice.claim_entity("Dragon")
            await asyncio.sleep(0.05)

            assert len(errors) >= 1
            assert "UNKNOWN_ENTITY" in str(errors[0].get("code", ""))

            await _cleanup(host, t1)

        event_loop.run_until_complete(_test())


# ---------------------------------------------------------------------------
# Phase 2 — Turn-Based Actions
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestTurnBasedActions:

    def test_action_on_correct_turn(self, event_loop, gamemaster):
        """Paladin (turn 0) sends END_TURN → success."""
        async def _test():
            server, host = await _setup(gamemaster)
            alice, t1 = await _connect(server, "Alice")

            await alice.claim_entity("Paladin")
            await asyncio.sleep(0.05)

            results = []
            alice.on(MessageType.ACTION_RESULT,
                     lambda msg: results.append(msg.payload))

            await alice.request_action("END_TURN", {})
            await asyncio.sleep(0.1)

            assert len(results) >= 1
            assert results[0]["success"] is True

            await _cleanup(host, t1)

        event_loop.run_until_complete(_test())

    def test_action_rejected_wrong_turn(self, event_loop, gamemaster):
        """After Paladin ends turn, Paladin's next action is rejected."""
        async def _test():
            server, host = await _setup(gamemaster)
            alice, t1 = await _connect(server, "Alice")
            bob, t2 = await _connect(server, "Bob")

            await alice.claim_entity("Paladin")
            await bob.claim_entity("Ranger")
            await asyncio.sleep(0.05)

            # Register error handler BEFORE sending actions
            errors = []
            alice.on(MessageType.ERROR, lambda msg: errors.append(msg.payload))

            # Paladin ends turn (turn 0 → turn 1)
            results = []
            alice.on(MessageType.ACTION_RESULT, lambda msg: results.append(msg.payload))
            await alice.request_action("END_TURN", {})
            await asyncio.sleep(0.15)

            # Now it's Ranger's turn — Paladin's action should fail
            await alice.request_action("END_TURN", {})
            await asyncio.sleep(0.15)

            assert len(errors) >= 1
            assert "turn" in str(errors[0].get("message", "")).lower()

            await _cleanup(host, t1, t2)

        event_loop.run_until_complete(_test())

    def test_move_action(self, event_loop, gamemaster):
        """Ranger moves to a new position."""
        async def _test():
            server, host = await _setup(gamemaster)
            alice, t1 = await _connect(server, "Alice")
            bob, t2 = await _connect(server, "Bob")

            await alice.claim_entity("Paladin")
            await bob.claim_entity("Ranger")
            await asyncio.sleep(0.05)

            # Register handlers BEFORE sending any actions
            alice_results = []
            alice.on(MessageType.ACTION_RESULT, lambda msg: alice_results.append(msg.payload))
            bob_results = []
            bob.on(MessageType.ACTION_RESULT, lambda msg: bob_results.append(msg.payload))

            # Paladin ends turn first
            await alice.request_action("END_TURN", {})
            await asyncio.sleep(0.15)

            # Now Ranger's turn — move to (2, 0)
            await bob.request_action("MOVE", {"position": [2, 0]})
            await asyncio.sleep(0.15)

            assert len(bob_results) >= 1
            assert bob_results[0]["success"] is True

            # Verify position updated on host
            ranger = next(e for e in gamemaster.game_entities if e.name == "Ranger")
            assert ranger.position == (2, 0)

            await _cleanup(host, t1, t2)

        event_loop.run_until_complete(_test())

    def test_attack_action(self, event_loop, gamemaster):
        """Paladin attacks Goblin — gets hit or miss result."""
        async def _test():
            # Place Goblin adjacent to Paladin for attack
            goblin = next(e for e in gamemaster.game_entities if e.name == "Goblin")
            gamemaster.world_tile_manager.move_entity(goblin, 0, 1)

            server, host = await _setup(gamemaster)
            alice, t1 = await _connect(server, "Alice")

            await alice.claim_entity("Paladin")
            await asyncio.sleep(0.05)

            results = []
            alice.on(MessageType.ACTION_RESULT,
                     lambda msg: results.append(msg.payload))
            await alice.request_action("ATTACK", {"target": "Goblin"})
            await asyncio.sleep(0.1)

            assert len(results) >= 1
            assert results[0]["success"] is True
            result_data = results[0].get("result", {})
            assert "action" in result_data
            assert result_data["action"] == "attack"
            assert "hit" in result_data

            await _cleanup(host, t1)

        event_loop.run_until_complete(_test())

    def test_unclaimed_entity_action_rejected(self, event_loop, gamemaster):
        """Client without a claimed entity cannot send actions."""
        async def _test():
            server, host = await _setup(gamemaster)
            alice, t1 = await _connect(server, "Alice")
            # Alice does NOT claim any entity

            errors = []
            alice.on(MessageType.ERROR, lambda msg: errors.append(msg.payload))
            await alice.request_action("END_TURN", {})
            await asyncio.sleep(0.1)

            assert len(errors) >= 1

            await _cleanup(host, t1)

        event_loop.run_until_complete(_test())


# ---------------------------------------------------------------------------
# Phase 3 — Communication
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestChat:

    def test_chat_broadcast(self, event_loop, gamemaster):
        """Alice sends chat, both Alice and Bob receive it."""
        async def _test():
            server, host = await _setup(gamemaster)
            alice, t1 = await _connect(server, "Alice")
            bob, t2 = await _connect(server, "Bob")

            alice_chats = []
            bob_chats = []
            alice.on(MessageType.CHAT, lambda msg: alice_chats.append(msg.payload))
            bob.on(MessageType.CHAT, lambda msg: bob_chats.append(msg.payload))

            await alice.send_chat("Hello from Alice!")
            await asyncio.sleep(0.1)

            assert len(bob_chats) >= 1
            assert bob_chats[0]["message"] == "Hello from Alice!"
            assert bob_chats[0]["sender"] == "Alice"

            # Alice also receives her own message (broadcast to all)
            assert len(alice_chats) >= 1

            await _cleanup(host, t1, t2)

        event_loop.run_until_complete(_test())

    def test_chat_from_both_clients(self, event_loop, gamemaster):
        """Both clients send and receive chat messages."""
        async def _test():
            server, host = await _setup(gamemaster)
            alice, t1 = await _connect(server, "Alice")
            bob, t2 = await _connect(server, "Bob")

            all_chats_alice = []
            all_chats_bob = []
            alice.on(MessageType.CHAT, lambda msg: all_chats_alice.append(msg.payload))
            bob.on(MessageType.CHAT, lambda msg: all_chats_bob.append(msg.payload))

            await alice.send_chat("Hi Bob!")
            await bob.send_chat("Hi Alice!")
            await asyncio.sleep(0.1)

            # Each should see both messages
            assert len(all_chats_alice) >= 2
            assert len(all_chats_bob) >= 2

            messages_alice = [c["message"] for c in all_chats_alice]
            assert "Hi Bob!" in messages_alice
            assert "Hi Alice!" in messages_alice

            await _cleanup(host, t1, t2)

        event_loop.run_until_complete(_test())


# ---------------------------------------------------------------------------
# Phase 4 — State Consistency
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestStateConsistency:

    def test_world_state_consistent_after_move(self, event_loop, gamemaster):
        """After a MOVE, host entity position matches the action."""
        async def _test():
            server, host = await _setup(gamemaster)
            alice, t1 = await _connect(server, "Alice")
            bob, t2 = await _connect(server, "Bob")

            await alice.claim_entity("Paladin")
            await bob.claim_entity("Ranger")
            await asyncio.sleep(0.05)

            # Register handlers before sending
            alice_results = []
            alice.on(MessageType.ACTION_RESULT, lambda msg: alice_results.append(msg.payload))
            bob_results = []
            bob.on(MessageType.ACTION_RESULT, lambda msg: bob_results.append(msg.payload))

            # Paladin ends turn
            await alice.request_action("END_TURN", {})
            await asyncio.sleep(0.15)

            # Ranger moves
            await bob.request_action("MOVE", {"position": [2, 0]})
            await asyncio.sleep(0.15)

            # Verify the move succeeded
            assert len(bob_results) >= 1
            assert bob_results[0]["success"] is True

            # Verify host world state
            ranger = next(e for e in gamemaster.game_entities if e.name == "Ranger")
            assert ranger.position == (2, 0)

            # Verify entity is tracked at new position on tile manager
            entities_at_new = gamemaster.world_tile_manager.entities.get((2, 0), [])
            assert any(e.name == "Ranger" for e in entities_at_new)

            # Verify entity is NOT at old position
            entities_at_old = gamemaster.world_tile_manager.entities.get((1, 0), [])
            assert not any(e.name == "Ranger" for e in entities_at_old)

            await _cleanup(host, t1, t2)

        event_loop.run_until_complete(_test())


# ---------------------------------------------------------------------------
# Phase 5 — Disconnect
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestDisconnect:

    def test_graceful_disconnect(self, event_loop, gamemaster):
        """Clients disconnect cleanly, host player count decreases."""
        async def _test():
            server, host = await _setup(gamemaster)
            alice, t1 = await _connect(server, "Alice")
            bob, t2 = await _connect(server, "Bob")

            assert len(host.players) == 2

            # Alice disconnects
            await alice.disconnect()
            await asyncio.sleep(0.1)
            t1.cancel()
            assert len(host.players) <= 1

            # Bob disconnects
            await bob.disconnect()
            await asyncio.sleep(0.1)
            t2.cancel()
            assert len(host.players) == 0

            await host.stop()

        event_loop.run_until_complete(_test())

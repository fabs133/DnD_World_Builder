"""Integration test: full player action flow over in-memory transport."""

import asyncio

import pytest

from network.transport import InMemoryServer, InMemoryClient
from network.session_host import SessionHost
from network.protocol import (
    Message, MessageType, CRITICAL_TYPES,
    make_hello, make_claim_entity, make_action_request, make_ack,
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


async def _recv_type(conn, target_type, timeout=5.0):
    """Read messages, auto-ACKing critical ones, skipping PING/PONG/ACK,
    until target_type arrives."""
    _SKIP = {MessageType.PING, MessageType.PONG, MessageType.ACK}
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise asyncio.TimeoutError(f"Timed out waiting for {target_type}")
        raw = await asyncio.wait_for(conn.recv(), timeout=remaining)
        msg = Message.from_json(raw)
        # Auto-ACK critical messages so the host's request() doesn't time out
        if msg.type in CRITICAL_TYPES and msg.seq:
            ack = make_ack(msg.seq)
            try:
                await conn.send(ack.to_json())
            except ConnectionError:
                pass
        if msg.type == target_type:
            return msg
        if msg.type in _SKIP:
            continue
        return msg


class _AutoResponder:
    """Background task that auto-ACKs critical messages and replies to PINGs.

    Queues application-level messages for the test to read via recv().
    """
    def __init__(self, conn):
        self.conn = conn
        self._app_queue = asyncio.Queue()
        self._task = None

    async def start(self):
        self._task = asyncio.ensure_future(self._loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass

    async def recv(self, timeout=5.0):
        return await asyncio.wait_for(self._app_queue.get(), timeout=timeout)

    async def send(self, data):
        await self.conn.send(data)

    async def _loop(self):
        _SKIP = {MessageType.PING, MessageType.PONG, MessageType.ACK}
        try:
            while True:
                raw = await self.conn.recv()
                msg = Message.from_json(raw)
                # Auto-ACK critical messages
                if msg.type in CRITICAL_TYPES and msg.seq:
                    await self.conn.send(make_ack(msg.seq).to_json())
                # Auto-reply to PING
                if msg.type == MessageType.PING:
                    pong = Message(type=MessageType.PONG)
                    await self.conn.send(pong.to_json())
                    continue
                if msg.type in _SKIP:
                    continue
                # Queue for the test
                await self._app_queue.put(msg)
        except (ConnectionError, asyncio.CancelledError):
            pass


async def _connect_and_claim(server, entity_name, player_name):
    """Connect, handshake, claim entity. Returns an _AutoResponder wrapper."""
    client = InMemoryClient(server)
    conn = await client.connect()
    await conn.send(make_hello(player_name).to_json())
    welcome = Message.from_json(await asyncio.wait_for(conn.recv(), timeout=2.0))
    if welcome.seq:
        await conn.send(make_ack(welcome.seq).to_json())
    full_state = Message.from_json(await asyncio.wait_for(conn.recv(), timeout=2.0))
    if full_state.seq:
        await conn.send(make_ack(full_state.seq).to_json())

    # Start auto-responder for background ACKs/PINGs
    responder = _AutoResponder(conn)
    await responder.start()

    await conn.send(make_claim_entity(entity_name).to_json())
    await asyncio.sleep(0.3)
    claimed = await responder.recv(timeout=5.0)
    assert claimed.type == MessageType.ENTITY_CLAIMED
    return responder, welcome


class TestNetworkedActions:

    def test_full_move_flow(self, event_loop, gamemaster):
        """Connect → claim → move → verify position changes on both sides."""
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            alice, _ = await _connect_and_claim(server, "Hero", "Alice")

            move_msg = make_action_request("MOVE", {"position": [3, 0]})
            await alice.send(move_msg.to_json())
            await asyncio.sleep(0.3)
            result = await alice.recv(timeout=5.0)
            assert result.type == MessageType.ACTION_RESULT
            assert result.payload["success"] is True

            hero = next(e for e in gamemaster.game_entities if e.name == "Hero")
            assert hero.position == (3, 0)

            await alice.stop()
            await host.stop()

        event_loop.run_until_complete(_test())

    def test_two_players_sequential_turns(self, event_loop, gamemaster):
        """Player 1 acts on their turn, player 2 gets rejected until their turn."""
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            # Alice claims Hero (turn 0)
            alice, _ = await _connect_and_claim(server, "Hero", "Alice")
            # Bob claims Goblin (turn 1)
            bob, _ = await _connect_and_claim(server, "Goblin", "Bob")

            # Let pending broadcasts settle
            await asyncio.sleep(0.5)

            # Drain any leftover ENTITY_CLAIMED broadcasts
            for resp in (alice, bob):
                try:
                    while True:
                        await asyncio.wait_for(resp._app_queue.get(), timeout=0.2)
                except asyncio.TimeoutError:
                    pass

            # Bob tries to act (Goblin) — should be rejected (it's Hero's turn)
            action_msg = make_action_request("END_TURN", {})
            await bob.send(action_msg.to_json())
            await asyncio.sleep(0.3)
            bob_result = await bob.recv(timeout=5.0)
            assert bob_result.type == MessageType.ERROR
            assert bob_result.payload["code"] == "NOT_YOUR_TURN"

            # Alice acts (Hero) — should succeed
            await alice.send(action_msg.to_json())
            await asyncio.sleep(0.3)
            alice_result = await alice.recv(timeout=5.0)
            assert alice_result.type == MessageType.ACTION_RESULT
            assert alice_result.payload["success"] is True

            await alice.stop()
            await bob.stop()
            await host.stop()

        event_loop.run_until_complete(_test())

    def test_action_result_contains_result_data(self, event_loop, gamemaster):
        """ACTION_RESULT for a move contains from/to positions."""
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()

            alice, _ = await _connect_and_claim(server, "Hero", "Alice")

            move_msg = make_action_request("MOVE", {"position": [2, 2]})
            await alice.send(move_msg.to_json())
            await asyncio.sleep(0.3)
            result = await alice.recv(timeout=5.0)

            assert result.type == MessageType.ACTION_RESULT
            assert result.payload["success"] is True
            assert result.payload["result"]["action"] == "move"
            assert result.payload["result"]["to"] == (2, 2) or result.payload["result"]["to"] == [2, 2]

            await alice.stop()
            await host.stop()

        event_loop.run_until_complete(_test())

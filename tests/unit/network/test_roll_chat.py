"""Tests for host-authoritative /roll in session chat."""

import asyncio
import random

import pytest

from core.engine.dice import format_roll, roll
from models.entities.game_entity import GameEntity
from models.game_master import Gamemaster
from network.protocol import Message, MessageType, make_chat, make_hello
from network.session_host import SessionHost
from network.transport import InMemoryClient, InMemoryServer


@pytest.fixture
def gamemaster():
    gm = Gamemaster()
    gm.add_entity(GameEntity("Hero", "player", stats={"hp": 20}))
    return gm


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def _connect(server, name):
    conn = await InMemoryClient(server).connect()
    await conn.send(make_hello(name).to_json())
    await asyncio.wait_for(conn.recv(), timeout=2.0)  # WELCOME
    await asyncio.wait_for(conn.recv(), timeout=2.0)  # FULL_STATE
    return conn


async def _recv(conn):
    return Message.from_json(await asyncio.wait_for(conn.recv(), timeout=2.0))


async def _assert_next_is_sentinel(host, conn):
    """The next message *conn* gets is a sentinel, i.e. nothing was queued."""
    await host.broadcast(make_chat("sentinel", "ping"))
    assert (await _recv(conn)).payload["sender"] == "sentinel"


def _expected(expr, seed=7):
    return format_roll(roll(expr, rng=random.Random(seed)))


class TestRollChat:
    def test_roll_broadcast_to_all(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server, rng=random.Random(7))
            await host.start()
            a = await _connect(server, "Alice")
            b = await _connect(server, "Bob")

            await a.send(make_chat("Alice", "/roll 2d6+3").to_json())
            for conn in (a, b):
                msg = await _recv(conn)
                assert msg.type == MessageType.CHAT
                assert msg.payload["sender"] == "\U0001f3b2 Alice"
                assert msg.payload["message"] == _expected("2d6+3")
            await host.stop()

        event_loop.run_until_complete(_test())

    def test_roll_is_case_insensitive(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server, rng=random.Random(7))
            await host.start()
            a = await _connect(server, "Alice")
            await a.send(make_chat("Alice", "/ROLL d20").to_json())
            msg = await _recv(a)
            assert msg.payload["message"] == _expected("d20")
            await host.stop()

        event_loop.run_until_complete(_test())

    def test_invalid_expression_only_to_sender(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server, rng=random.Random(7))
            await host.start()
            a = await _connect(server, "Alice")
            b = await _connect(server, "Bob")

            await a.send(make_chat("Alice", "/roll banana").to_json())
            msg = await _recv(a)
            assert msg.type == MessageType.CHAT
            assert msg.payload["sender"] == "\U0001f3b2"
            assert msg.payload["message"]
            await _assert_next_is_sentinel(host, b)
            await host.stop()

        event_loop.run_until_complete(_test())

    def test_normal_chat_unchanged(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server)
            await host.start()
            a = await _connect(server, "Alice")
            b = await _connect(server, "Bob")

            await a.send(make_chat("Alice", "rolling around /roll").to_json())
            for conn in (a, b):
                msg = await _recv(conn)
                assert msg.payload["sender"] == "Alice"
                assert msg.payload["message"] == "rolling around /roll"
            await host.stop()

        event_loop.run_until_complete(_test())

    def test_host_chat_roll_broadcasts_and_returns(self, event_loop, gamemaster):
        async def _test():
            server = InMemoryServer()
            host = SessionHost(gamemaster, server, rng=random.Random(7))
            await host.start()
            a = await _connect(server, "Alice")

            chat = await host.host_chat("DM", "/roll d20")
            assert chat.payload["sender"] == "\U0001f3b2 DM"
            assert chat.payload["message"] == _expected("d20")
            assert (await _recv(a)).payload == chat.payload

            err = await host.host_chat("DM", "/roll nope")
            assert err.payload["sender"] == "\U0001f3b2"
            await _assert_next_is_sentinel(host, a)
            await host.stop()

        event_loop.run_until_complete(_test())

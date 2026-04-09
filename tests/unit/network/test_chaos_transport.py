"""Tests for ChaosTransport fault injection layer."""

import asyncio
import time

import pytest

from network.transport import InMemoryTransportPair, InMemoryServer, InMemoryClient
from network.chaos_transport import (
    ChaosConnection, ChaosClient, ChaosScenario,
    CLEAN, HIGH_LATENCY, SUDDEN_DISCONNECT, SLOW_LOSSY,
)


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestChaosConnection:

    def test_clean_passthrough(self, event_loop):
        async def _test():
            a, b = InMemoryTransportPair.create()
            chaos = ChaosConnection(a, CLEAN)
            for i in range(20):
                await chaos.send(f"msg_{i}")
                result = await b.recv()
                assert result == f"msg_{i}"

        event_loop.run_until_complete(_test())

    def test_delay_adds_latency(self, event_loop):
        async def _test():
            a, b = InMemoryTransportPair.create()
            scenario = ChaosScenario(name="test_delay", delay_ms=50)
            chaos = ChaosConnection(a, scenario)

            t0 = time.perf_counter()
            await chaos.send("hello")
            elapsed = time.perf_counter() - t0
            assert elapsed >= 0.045, f"Expected >= 45ms, got {elapsed*1000:.0f}ms"

            # Verify data actually arrived
            result = await b.recv()
            assert result == "hello"

        event_loop.run_until_complete(_test())

    def test_disconnect_at_threshold(self, event_loop):
        async def _test():
            a, b = InMemoryTransportPair.create()
            scenario = ChaosScenario(name="test_dc", disconnect_after=5)
            chaos = ChaosConnection(a, scenario)

            # First 5 sends succeed (indices 0-4)
            for i in range(5):
                await chaos.send(f"msg_{i}")

            # 6th send (index 5, but _send_count is now 5) triggers disconnect
            with pytest.raises(ConnectionError):
                await chaos.send("should_fail")

            assert chaos.closed

        event_loop.run_until_complete(_test())

    def test_recv_delay(self, event_loop):
        async def _test():
            a, b = InMemoryTransportPair.create()
            scenario = ChaosScenario(name="test_recv", delay_ms=50)
            chaos_b = ChaosConnection(b, scenario)

            await a.send("data")

            t0 = time.perf_counter()
            result = await chaos_b.recv()
            elapsed = time.perf_counter() - t0
            assert elapsed >= 0.045
            assert result == "data"

        event_loop.run_until_complete(_test())

    def test_close_delegates(self, event_loop):
        async def _test():
            a, b = InMemoryTransportPair.create()
            chaos = ChaosConnection(a, CLEAN)
            assert not chaos.closed
            await chaos.close()
            assert chaos.closed
            assert a.closed

        event_loop.run_until_complete(_test())

    def test_send_after_close_raises(self, event_loop):
        async def _test():
            a, b = InMemoryTransportPair.create()
            chaos = ChaosConnection(a, CLEAN)
            await chaos.close()
            with pytest.raises(ConnectionError):
                await chaos.send("nope")

        event_loop.run_until_complete(_test())


class TestChaosClient:

    def test_connect_wraps_in_chaos(self, event_loop):
        async def _test():
            server = InMemoryServer()
            received = []

            async def handler(conn):
                msg = await conn.recv()
                received.append(msg)
                await conn.send(f"echo:{msg}")

            server.on_connection(handler)

            inner_client = InMemoryClient(server)
            chaos_client = ChaosClient(inner_client, HIGH_LATENCY)
            conn = await chaos_client.connect()

            assert isinstance(conn, ChaosConnection)

            await conn.send("ping")
            reply = await conn.recv()
            assert reply == "echo:ping"
            assert received == ["ping"]

        event_loop.run_until_complete(_test())

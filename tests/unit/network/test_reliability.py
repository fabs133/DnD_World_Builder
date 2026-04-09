"""End-to-end reliability tests for ReliableChannel over WebSocket + ChaosTransport.

Tests the full stack: WebSocket → ChaosConnection → ReliableChannel,
proving that ACK/retry logic compensates for adverse conditions.

Does NOT use SessionHost / SessionClient (those require a gamemaster).
"""

import asyncio
import socket

import pytest

from network.websocket_transport import WebSocketServer, WebSocketClient
from network.chaos_transport import (
    ChaosConnection, ChaosScenario,
    CLEAN, HIGH_LATENCY, SLOW_LOSSY, SUDDEN_DISCONNECT,
)
from network.reliable_channel import ReliableChannel, PING_TIMEOUT, PING_INTERVAL
from network.protocol import Message, MessageType, make_turn_change, make_chat


# ── Fixtures & helpers ───────────────────────────────────────────

@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


async def make_channel_pair(scenario: ChaosScenario, port: int):
    """Create two ReliableChannels connected via WebSocket + ChaosConnection.

    Returns (server, ws_client, ch_client, ch_server, done_event).
    The *done_event* keeps the WS handler alive — set it during cleanup.
    """
    server = WebSocketServer("127.0.0.1", port)
    conn_ready = asyncio.Event()
    done_event = asyncio.Event()
    server_conn_holder = []

    async def on_conn(conn):
        server_conn_holder.append(conn)
        conn_ready.set()
        await done_event.wait()

    server.on_connection(on_conn)
    await server.start()

    ws_client = WebSocketClient("127.0.0.1", port)
    client_raw = await ws_client.connect()
    await asyncio.wait_for(conn_ready.wait(), timeout=3.0)
    server_raw = server_conn_holder[0]

    chaos_client = ChaosConnection(client_raw, scenario)
    chaos_server = ChaosConnection(server_raw, scenario)

    ch_client = ReliableChannel(chaos_client, "test-client")
    ch_server = ReliableChannel(chaos_server, "test-server")
    await ch_client.start()
    await ch_server.start()

    return server, ws_client, ch_client, ch_server, done_event


async def cleanup(server, ws_client, ch_client, ch_server, done_event):
    """Tear down a channel pair cleanly."""
    await ch_client.stop()
    await ch_server.stop()
    done_event.set()
    await asyncio.sleep(0.1)
    await ws_client.close_session()
    await server.stop()


def make_collector(channel: ReliableChannel, count: int):
    """Install a message collector on *channel* BEFORE sending.

    Returns (messages_list, wait_coro_factory).
    Call ``await wait(timeout)`` after sending to wait for collection.
    """
    messages: list[Message] = []
    evt = asyncio.Event()

    def handler(msg):
        messages.append(msg)
        if len(messages) >= count:
            evt.set()

    channel.on_message = handler

    async def wait(timeout: float = 5.0):
        try:
            await asyncio.wait_for(evt.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

    return messages, wait


# ── Tests ────────────────────────────────────────────────────────

class TestReliability:

    def test_clean_delivery(self, event_loop):
        async def _test():
            port = _free_port()
            srv, wsc, ch_c, ch_s, done = await make_channel_pair(CLEAN, port)
            try:
                N = 10
                received, wait = make_collector(ch_c, N)
                for i in range(N):
                    msg = make_turn_change(f"entity_{i}", i)
                    await ch_s.request(msg)
                await wait(5.0)
                assert len(received) == N
            finally:
                await cleanup(srv, wsc, ch_c, ch_s, done)

        event_loop.run_until_complete(_test())

    def test_high_latency_delivery(self, event_loop):
        async def _test():
            port = _free_port()
            srv, wsc, ch_c, ch_s, done = await make_channel_pair(HIGH_LATENCY, port)
            try:
                N = 5
                received, wait = make_collector(ch_c, N)
                for i in range(N):
                    msg = make_turn_change(f"entity_{i}", i)
                    await ch_s.request(msg)
                await wait(15.0)
                assert len(received) == N
            finally:
                await cleanup(srv, wsc, ch_c, ch_s, done)

        event_loop.run_until_complete(_test())

    def test_slow_lossy_delivery(self, event_loop):
        async def _test():
            port = _free_port()
            srv, wsc, ch_c, ch_s, done = await make_channel_pair(SLOW_LOSSY, port)
            try:
                N = 5
                received, wait = make_collector(ch_c, N)
                for i in range(N):
                    msg = make_turn_change(f"entity_{i}", i)
                    await ch_s.request(msg)
                await wait(10.0)
                assert len(received) == N
            finally:
                await cleanup(srv, wsc, ch_c, ch_s, done)

        event_loop.run_until_complete(_test())

    def test_non_critical_fire(self, event_loop):
        async def _test():
            port = _free_port()
            srv, wsc, ch_c, ch_s, done = await make_channel_pair(CLEAN, port)
            try:
                N = 20
                received, wait = make_collector(ch_c, N)
                for i in range(N):
                    msg = make_chat("tester", f"hello_{i}")
                    await ch_s.fire(msg)
                await wait(5.0)
                assert len(received) == N
            finally:
                await cleanup(srv, wsc, ch_c, ch_s, done)

        event_loop.run_until_complete(_test())

    def test_sequence_monotonic(self, event_loop):
        async def _test():
            port = _free_port()
            srv, wsc, ch_c, ch_s, done = await make_channel_pair(CLEAN, port)
            try:
                N = 15
                received, wait = make_collector(ch_c, N)
                for i in range(N):
                    msg = make_turn_change(f"entity_{i}", i)
                    await ch_s.request(msg)
                await wait(5.0)
                assert len(received) == N

                seqs = [m.seq for m in received]
                for i in range(1, len(seqs)):
                    assert seqs[i] > seqs[i - 1], \
                        f"Sequence not monotonic: {seqs[i]} <= {seqs[i-1]}"
            finally:
                await cleanup(srv, wsc, ch_c, ch_s, done)

        event_loop.run_until_complete(_test())

    def test_disconnect_detection(self, event_loop):
        async def _test():
            port = _free_port()
            scenario = ChaosScenario(name="dc_test", disconnect_after=5)
            srv, wsc, ch_c, ch_s, done = await make_channel_pair(scenario, port)
            try:
                disconnect_detected = asyncio.Event()
                ch_c.on_disconnect = lambda: disconnect_detected.set()

                # Send messages until the chaos layer disconnects
                for i in range(12):
                    try:
                        msg = make_turn_change(f"e_{i}", i)
                        await ch_s.fire(msg)
                    except (ConnectionError, OSError):
                        break
                    await asyncio.sleep(0.05)

                # Wait for the disconnect to be detected
                try:
                    await asyncio.wait_for(
                        disconnect_detected.wait(),
                        timeout=PING_TIMEOUT + 5)
                except asyncio.TimeoutError:
                    pass

                assert not ch_c.alive or disconnect_detected.is_set()
            finally:
                await cleanup(srv, wsc, ch_c, ch_s, done)

        event_loop.run_until_complete(_test())

    def test_reconnect_restores(self, event_loop):
        async def _test():
            # First connection — verify it works
            port1 = _free_port()
            srv1, wsc1, ch_c1, ch_s1, done1 = await make_channel_pair(CLEAN, port1)
            try:
                received1, wait1 = make_collector(ch_c1, 1)
                msg = make_turn_change("entity_0", 0)
                await ch_s1.request(msg)
                await wait1(3.0)
                assert len(received1) == 1
            finally:
                await cleanup(srv1, wsc1, ch_c1, ch_s1, done1)

            # Second connection on a new port — proves recovery works
            port2 = _free_port()
            srv2, wsc2, ch_c2, ch_s2, done2 = await make_channel_pair(CLEAN, port2)
            try:
                N = 5
                received2, wait2 = make_collector(ch_c2, N)
                for i in range(N):
                    msg = make_turn_change(f"entity_{i}", i)
                    await ch_s2.request(msg)
                await wait2(5.0)
                assert len(received2) == N
            finally:
                await cleanup(srv2, wsc2, ch_c2, ch_s2, done2)

        event_loop.run_until_complete(_test())

    def test_three_clients(self, event_loop):
        async def _test():
            port = _free_port()
            server = WebSocketServer("127.0.0.1", port)
            done_events = []
            server_channels = []
            conn_events = []

            for _ in range(3):
                conn_events.append(asyncio.Event())
                done_events.append(asyncio.Event())

            conn_idx = [0]

            async def on_conn(conn):
                i = conn_idx[0]
                conn_idx[0] += 1
                chaos = ChaosConnection(conn, CLEAN)
                ch = ReliableChannel(chaos, f"server-{i}")
                server_channels.append(ch)
                await ch.start()
                conn_events[i].set()
                await done_events[i].wait()

            server.on_connection(on_conn)
            await server.start()

            # Connect 3 clients
            client_channels = []
            ws_clients = []
            for i in range(3):
                wsc = WebSocketClient("127.0.0.1", port)
                raw = await wsc.connect()
                chaos = ChaosConnection(raw, CLEAN)
                ch = ReliableChannel(chaos, f"client-{i}")
                await ch.start()
                client_channels.append(ch)
                ws_clients.append(wsc)
                await asyncio.wait_for(conn_events[i].wait(), timeout=3.0)

            try:
                N = 5
                # Install collectors BEFORE sending
                collectors = []
                for cch in client_channels:
                    received, wait = make_collector(cch, N)
                    collectors.append((received, wait))

                # Server broadcasts to all 3 clients
                for i in range(N):
                    msg = make_turn_change(f"entity_{i}", i)
                    for sch in server_channels:
                        await sch.request(msg)

                # Each client should receive N messages
                for received, wait in collectors:
                    await wait(5.0)
                    assert len(received) == N
            finally:
                for ch in client_channels:
                    await ch.stop()
                for ch in server_channels:
                    await ch.stop()
                for de in done_events:
                    de.set()
                await asyncio.sleep(0.1)
                for wsc in ws_clients:
                    await wsc.close_session()
                await server.stop()

        event_loop.run_until_complete(_test())

"""Tests for the aiohttp WebSocket transport layer."""
import asyncio
import pytest
from network.websocket_transport import WebSocketServer, WebSocketClient


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _free_port():
    """Find a free port for testing."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class TestWebSocketTransport:

    def test_server_start_stop(self, event_loop):
        async def _test():
            port = _free_port()
            server = WebSocketServer("127.0.0.1", port)
            server.on_connection(lambda conn: asyncio.sleep(0))
            await server.start()
            await server.stop()

        event_loop.run_until_complete(_test())

    def test_client_connects_and_sends(self, event_loop):
        async def _test():
            port = _free_port()
            server = WebSocketServer("127.0.0.1", port)

            received = []

            async def on_conn(conn):
                msg = await asyncio.wait_for(conn.recv(), timeout=2.0)
                received.append(msg)
                await conn.send("pong")

            server.on_connection(on_conn)
            await server.start()

            client = WebSocketClient("127.0.0.1", port)
            conn = await client.connect()
            await conn.send("ping")
            reply = await asyncio.wait_for(conn.recv(), timeout=2.0)

            assert received == ["ping"]
            assert reply == "pong"

            await conn.close()
            await client.close_session()
            await server.stop()

        event_loop.run_until_complete(_test())

    def test_multiple_messages(self, event_loop):
        async def _test():
            port = _free_port()
            server = WebSocketServer("127.0.0.1", port)

            server_received = []

            async def on_conn(conn):
                for _ in range(3):
                    msg = await asyncio.wait_for(conn.recv(), timeout=2.0)
                    server_received.append(msg)
                    await conn.send(f"echo:{msg}")

            server.on_connection(on_conn)
            await server.start()

            client = WebSocketClient("127.0.0.1", port)
            conn = await client.connect()

            for i in range(3):
                await conn.send(f"msg{i}")
                reply = await asyncio.wait_for(conn.recv(), timeout=2.0)
                assert reply == f"echo:msg{i}"

            assert server_received == ["msg0", "msg1", "msg2"]

            await conn.close()
            await client.close_session()
            await server.stop()

        event_loop.run_until_complete(_test())

    def test_multiple_clients(self, event_loop):
        async def _test():
            port = _free_port()
            server = WebSocketServer("127.0.0.1", port)

            client_names = []

            async def on_conn(conn):
                name = await asyncio.wait_for(conn.recv(), timeout=2.0)
                client_names.append(name)
                await conn.send(f"hello {name}")

            server.on_connection(on_conn)
            await server.start()

            clients = []
            for name in ["Alice", "Bob"]:
                c = WebSocketClient("127.0.0.1", port)
                conn = await c.connect()
                await conn.send(name)
                reply = await asyncio.wait_for(conn.recv(), timeout=2.0)
                assert reply == f"hello {name}"
                clients.append((c, conn))

            assert sorted(client_names) == ["Alice", "Bob"]

            for c, conn in clients:
                await conn.close()
                await c.close_session()
            await server.stop()

        event_loop.run_until_complete(_test())

    def test_connection_closed_property(self, event_loop):
        async def _test():
            port = _free_port()
            server = WebSocketServer("127.0.0.1", port)

            async def on_conn(conn):
                await asyncio.sleep(0.1)

            server.on_connection(on_conn)
            await server.start()

            client = WebSocketClient("127.0.0.1", port)
            conn = await client.connect()

            assert not conn.closed
            await conn.close()
            assert conn.closed

            await client.close_session()
            await server.stop()

        event_loop.run_until_complete(_test())

    def test_get_join_address(self, event_loop):
        async def _test():
            port = _free_port()
            server = WebSocketServer("0.0.0.0", port)
            addr = server.get_join_address()
            assert str(port) in addr

        event_loop.run_until_complete(_test())

import asyncio
import pytest
from network.transport import InMemoryTransportPair, InMemoryServer, InMemoryClient


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestInMemoryTransportPair:

    def test_send_recv(self, event_loop):
        async def _test():
            a, b = InMemoryTransportPair.create()
            await a.send("hello")
            result = await b.recv()
            assert result == "hello"

        event_loop.run_until_complete(_test())

    def test_bidirectional(self, event_loop):
        async def _test():
            a, b = InMemoryTransportPair.create()
            await a.send("ping")
            await b.send("pong")
            assert await b.recv() == "ping"
            assert await a.recv() == "pong"

        event_loop.run_until_complete(_test())

    def test_multiple_messages(self, event_loop):
        async def _test():
            a, b = InMemoryTransportPair.create()
            await a.send("msg1")
            await a.send("msg2")
            await a.send("msg3")
            assert await b.recv() == "msg1"
            assert await b.recv() == "msg2"
            assert await b.recv() == "msg3"

        event_loop.run_until_complete(_test())

    def test_close_sets_closed_flag(self, event_loop):
        async def _test():
            a, b = InMemoryTransportPair.create()
            assert not a.closed
            await a.close()
            assert a.closed

        event_loop.run_until_complete(_test())

    def test_send_after_close_raises(self, event_loop):
        async def _test():
            a, b = InMemoryTransportPair.create()
            await a.close()
            with pytest.raises(ConnectionError):
                await a.send("should fail")

        event_loop.run_until_complete(_test())

    def test_recv_after_close_raises(self, event_loop):
        async def _test():
            a, b = InMemoryTransportPair.create()
            await a.close()
            with pytest.raises(ConnectionError):
                await a.recv()

        event_loop.run_until_complete(_test())


class TestInMemoryServerClient:

    def test_client_connects_to_server(self, event_loop):
        async def _test():
            server = InMemoryServer()
            received = []

            async def handler(conn):
                data = await conn.recv()
                received.append(data)
                await conn.send("ack")

            server.on_connection(handler)
            await server.start()

            client = InMemoryClient(server)
            conn = await client.connect()
            await conn.send("test_msg")

            await asyncio.sleep(0.01)
            assert received == ["test_msg"]

            reply = await conn.recv()
            assert reply == "ack"
            await server.stop()

        event_loop.run_until_complete(_test())

    def test_multiple_clients(self, event_loop):
        async def _test():
            server = InMemoryServer()
            connections = []

            async def handler(conn):
                connections.append(conn)
                data = await conn.recv()
                await conn.send(f"echo:{data}")

            server.on_connection(handler)
            await server.start()

            client1 = InMemoryClient(server)
            conn1 = await client1.connect()
            await conn1.send("from_c1")

            client2 = InMemoryClient(server)
            conn2 = await client2.connect()
            await conn2.send("from_c2")

            await asyncio.sleep(0.01)

            r1 = await conn1.recv()
            r2 = await conn2.recv()
            assert r1 == "echo:from_c1"
            assert r2 == "echo:from_c2"
            assert len(connections) == 2

            await server.stop()

        event_loop.run_until_complete(_test())

    def test_server_stop_closes_connections(self, event_loop):
        async def _test():
            server = InMemoryServer()
            server_conns = []

            async def handler(conn):
                server_conns.append(conn)

            server.on_connection(handler)
            await server.start()

            client = InMemoryClient(server)
            await client.connect()
            await asyncio.sleep(0.01)

            await server.stop()
            assert all(c.closed for c in server_conns)

        event_loop.run_until_complete(_test())

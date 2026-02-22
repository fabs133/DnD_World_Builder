"""
Transport Abstraction Layer
===========================

Defines the abstract base classes for network transport, plus
in-memory implementations used for deterministic, socket-free testing.

The three ABCs — :class:`TransportConnection`, :class:`TransportServer`,
and :class:`TransportClient` — form the pluggable transport interface.
Real implementations (e.g. :mod:`network.websocket_transport`) and test
implementations (:class:`InMemoryServer` / :class:`InMemoryClient`) both
implement these ABCs, allowing protocol and session code to be tested
without real I/O.
"""

import asyncio
from abc import ABC, abstractmethod


class TransportConnection(ABC):
    """A single endpoint of a bidirectional connection.

    Implementations wrap real sockets or in-memory queues.
    """

    @abstractmethod
    async def send(self, data: str) -> None:
        """Send a message string to the remote endpoint.

        :param data: The message string to send (typically JSON).
        :type data: str
        :raises ConnectionError: If the connection is closed.
        """
        ...

    @abstractmethod
    async def recv(self) -> str:
        """Wait for and return the next message from the remote endpoint.

        :return: The received message string.
        :rtype: str
        :raises ConnectionError: If the connection is closed or lost.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close this connection."""
        ...

    @property
    @abstractmethod
    def closed(self) -> bool:
        """Whether this connection has been closed.

        :rtype: bool
        """
        ...


class TransportServer(ABC):
    """Accepts incoming connections.

    Subclasses must call the registered handler for each new connection.
    """

    @abstractmethod
    async def start(self) -> None:
        """Start listening for connections."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the server and close all active connections."""
        ...

    @abstractmethod
    def on_connection(self, handler) -> None:
        """Register an async handler called with each new :class:`TransportConnection`.

        :param handler: Coroutine function accepting a single
            :class:`TransportConnection` argument.
        :type handler: callable
        """
        ...


class TransportClient(ABC):
    """Connects to a server, producing a :class:`TransportConnection`."""

    @abstractmethod
    async def connect(self) -> TransportConnection:
        """Open a connection to the server.

        :return: A connected transport endpoint.
        :rtype: TransportConnection
        """
        ...


# --- In-memory implementations for testing ---

class _QueueConnection(TransportConnection):
    """TransportConnection backed by ``asyncio.Queue`` pairs (no real I/O).

    :param send_queue: Queue for outgoing messages.
    :type send_queue: asyncio.Queue
    :param recv_queue: Queue for incoming messages.
    :type recv_queue: asyncio.Queue
    """

    def __init__(self, send_queue: asyncio.Queue, recv_queue: asyncio.Queue):
        self._send_q = send_queue
        self._recv_q = recv_queue
        self._closed = False

    async def send(self, data: str) -> None:
        if self._closed:
            raise ConnectionError("Connection is closed")
        await self._send_q.put(data)

    async def recv(self) -> str:
        if self._closed:
            raise ConnectionError("Connection is closed")
        try:
            return await self._recv_q.get()
        except asyncio.CancelledError:
            raise ConnectionError("Connection closed during recv")

    async def close(self) -> None:
        self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed


class InMemoryTransportPair:
    """Creates a matched pair of connections linked by queues.

    Used internally by :class:`InMemoryClient` to simulate a network
    connection within a single process.
    """

    @staticmethod
    def create():
        """Create two cross-linked :class:`_QueueConnection` instances.

        :return: A ``(conn_a, conn_b)`` tuple where sending on ``conn_a``
            delivers to ``conn_b.recv()`` and vice versa.
        :rtype: tuple[_QueueConnection, _QueueConnection]
        """
        q_a_to_b = asyncio.Queue()
        q_b_to_a = asyncio.Queue()
        conn_a = _QueueConnection(q_a_to_b, q_b_to_a)
        conn_b = _QueueConnection(q_b_to_a, q_a_to_b)
        return conn_a, conn_b


class InMemoryServer(TransportServer):
    """In-memory server for testing. Clients connect via :class:`InMemoryClient`."""

    def __init__(self):
        self._handler = None
        self._connections = []

    async def start(self):
        pass

    async def stop(self):
        for conn in self._connections:
            await conn.close()

    def on_connection(self, handler):
        self._handler = handler

    async def accept(self, server_conn: TransportConnection):
        """Called internally when a client connects.

        :param server_conn: The server-side connection endpoint.
        :type server_conn: TransportConnection
        """
        self._connections.append(server_conn)
        if self._handler:
            await self._handler(server_conn)


class InMemoryClient(TransportClient):
    """In-memory client that connects to an :class:`InMemoryServer`.

    :param server: The server to connect to.
    :type server: InMemoryServer
    """

    def __init__(self, server: InMemoryServer):
        self._server = server
        self.connection = None

    async def connect(self) -> TransportConnection:
        """Create a paired connection and register with the server.

        :return: The client-side connection endpoint.
        :rtype: TransportConnection
        """
        client_conn, server_conn = InMemoryTransportPair.create()
        self.connection = client_conn
        asyncio.ensure_future(self._server.accept(server_conn))
        return client_conn

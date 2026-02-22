"""
WebSocket Transport
===================

Real network transport implemented with `aiohttp <https://docs.aiohttp.org>`_.

Provides concrete implementations of
:class:`~network.transport.TransportConnection`,
:class:`~network.transport.TransportServer`, and
:class:`~network.transport.TransportClient` that communicate over
WebSocket connections.

The server exposes a ``/ws`` HTTP endpoint.  Each accepted WebSocket is
wrapped in a :class:`WebSocketConnection` that feeds incoming messages into
an :class:`asyncio.Queue` via a background reader task.
"""

import asyncio
import logging
import socket

import aiohttp
from aiohttp import web

from network.transport import TransportConnection, TransportServer, TransportClient

logger = logging.getLogger(__name__)


class WebSocketConnection(TransportConnection):
    """Wraps an aiohttp WebSocket (server- or client-side).

    Incoming messages are read by a background :class:`asyncio.Task` and
    placed into an internal :class:`asyncio.Queue` so that :meth:`recv`
    never blocks the event loop.

    :param ws: The underlying aiohttp WebSocket response.
    """

    def __init__(self, ws):
        self._ws = ws
        self._closed = False
        self._recv_queue = asyncio.Queue()
        self._reader_task = None

    def start_reading(self, loop=None):
        """Start a background task that reads WS frames into the recv queue.

        :param loop: Unused; kept for API compatibility.
        """
        self._reader_task = asyncio.ensure_future(self._read_loop())

    async def _read_loop(self):
        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._recv_queue.put(msg.data)
                elif msg.type in (
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.CLOSING,
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.ERROR,
                ):
                    break
        except Exception:
            pass
        finally:
            self._closed = True
            # Unblock any pending recv()
            await self._recv_queue.put(None)

    async def send(self, data: str) -> None:
        """Send a text message over the WebSocket.

        :param data: The text payload to send.
        :type data: str
        :raises ConnectionError: If the connection is already closed.
        """
        if self._closed:
            raise ConnectionError("Connection is closed")
        await self._ws.send_str(data)

    async def recv(self) -> str:
        """Wait for and return the next text message.

        :return: The received text payload.
        :rtype: str
        :raises ConnectionError: If the connection is closed with no queued data.
        """
        if self._closed and self._recv_queue.empty():
            raise ConnectionError("Connection is closed")
        item = await self._recv_queue.get()
        if item is None:
            raise ConnectionError("Connection closed")
        return item

    async def close(self) -> None:
        """Close the WebSocket and cancel the background reader."""
        if not self._closed:
            self._closed = True
            try:
                await self._ws.close()
            except Exception:
                pass
            if self._reader_task and not self._reader_task.done():
                self._reader_task.cancel()

    @property
    def closed(self) -> bool:
        return self._closed


def _get_local_ip() -> str:
    """Get this machine's LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class WebSocketServer(TransportServer):
    """aiohttp-based WebSocket server implementing :class:`~network.transport.TransportServer`.

    Listens on the given *host* and *port*, accepting WebSocket connections at
    the ``/ws`` endpoint.

    :param host: Bind address (default ``"0.0.0.0"`` for all interfaces).
    :type host: str
    :param port: TCP port to listen on.
    :type port: int
    """

    def __init__(self, host="0.0.0.0", port=8765):
        self._host = host
        self._port = port
        self._handler = None
        self._app = None
        self._runner = None
        self._site = None
        self._connections = []

    async def start(self) -> None:
        """Create the aiohttp application and begin listening for connections."""
        self._app = web.Application()
        self._app.router.add_get("/ws", self._handle_ws)
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()
        logger.info(f"WebSocket server listening on {self._host}:{self._port}")

    async def stop(self) -> None:
        """Close all active connections and shut down the HTTP server."""
        for conn in self._connections:
            await conn.close()
        self._connections.clear()
        if self._runner:
            await self._runner.cleanup()
        logger.info("WebSocket server stopped")

    def on_connection(self, handler) -> None:
        """Register a coroutine to handle each new WebSocket connection.

        :param handler: An ``async def handler(conn)`` coroutine.
        """
        self._handler = handler

    def get_join_address(self) -> str:
        """Return a ``host:port`` string that clients can use to connect.

        :rtype: str
        """
        return f"{_get_local_ip()}:{self._port}"

    async def _handle_ws(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        conn = WebSocketConnection(ws)
        conn.start_reading()
        self._connections.append(conn)

        if self._handler:
            await self._handler(conn)

        self._connections.remove(conn) if conn in self._connections else None
        return ws


class WebSocketClient(TransportClient):
    """aiohttp-based WebSocket client implementing :class:`~network.transport.TransportClient`.

    :param host: The server hostname or IP to connect to.
    :type host: str
    :param port: The server port.
    :type port: int
    """

    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self._session = None

    async def connect(self) -> TransportConnection:
        """Open a WebSocket connection to the server.

        :return: A connection object for sending and receiving messages.
        :rtype: WebSocketConnection
        """
        url = f"http://{self._host}:{self._port}/ws"
        self._session = aiohttp.ClientSession()
        ws = await self._session.ws_connect(url)
        conn = WebSocketConnection(ws)
        conn.start_reading()
        return conn

    async def close_session(self):
        """Close the underlying :class:`aiohttp.ClientSession`."""
        if self._session:
            await self._session.close()
            self._session = None

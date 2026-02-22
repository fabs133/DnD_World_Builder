"""
Session Manager
===============

Orchestrates the full multiplayer host/client lifecycle.

Runs an :mod:`asyncio` event loop in a background daemon thread and uses
Qt signals (:class:`~PyQt5.QtCore.pyqtSignal`) to safely communicate from
async callbacks back to the main UI thread.

In **host mode** the manager spins up a
:class:`~network.websocket_transport.WebSocketServer`,
:class:`~network.session_host.SessionHost`, and the
:class:`~network.event_bridge.EventBridge` / :class:`~network.event_bridge.TurnBridge`.

In **client mode** it creates a
:class:`~network.session_client.SessionClient` and starts a listen loop.
"""

import asyncio
import logging
import threading

from PyQt5.QtCore import QObject, pyqtSignal

from network.protocol import MessageType

logger = logging.getLogger(__name__)


class SessionSignals(QObject):
    """Qt signals emitted from the network thread, delivered to the UI thread.

    All signals are thread-safe and can be connected to slots on the main
    thread from within the ``SessionManager`` async callbacks.
    """
    #: Emitted when a player connects (player_id, player_name).
    player_connected = pyqtSignal(str, str)
    #: Emitted when a player disconnects (player_id).
    player_disconnected = pyqtSignal(str)
    #: Emitted when an entity is claimed (entity_id, player_id).
    entity_claimed = pyqtSignal(str, str)
    #: Emitted when a chat message arrives (sender, message).
    chat_received = pyqtSignal(str, str)
    #: Emitted when the world state has changed.
    state_updated = pyqtSignal()
    #: Emitted on connection failure (error message).
    connection_error = pyqtSignal(str)
    #: Emitted when the client has connected successfully.
    connected = pyqtSignal()
    #: Emitted when the client has disconnected.
    disconnected = pyqtSignal()


class SessionManager:
    """Manages the full multiplayer session lifecycle.

    In **host mode** (DM): starts a WebSocket server,
    :class:`~network.session_host.SessionHost`,
    :class:`~network.event_bridge.EventBridge`, and
    :class:`~network.event_bridge.TurnBridge`.

    In **client mode** (Player): connects a
    :class:`~network.session_client.SessionClient` to a remote host.

    The :mod:`asyncio` event loop runs in a background daemon thread.  All UI
    communication goes through :class:`SessionSignals`
    (:class:`~PyQt5.QtCore.pyqtSignal`), which are thread-safe in Qt.

    :param gamemaster: Gamemaster instance (required for hosting).
    :param settings: :class:`~core.settings_manager.SettingsManager` for defaults.
    :param transport_factory: Optional callable used for testing with
        :class:`~network.transport.InMemoryTransportPair`.  When *None* the
        real :class:`~network.websocket_transport.WebSocketServer` /
        :class:`~network.websocket_transport.WebSocketClient` are used.
    """

    def __init__(self, gamemaster=None, settings=None, transport_factory=None):
        self.gamemaster = gamemaster
        self.settings = settings
        self.signals = SessionSignals()

        self._transport_factory = transport_factory
        self._loop = None
        self._thread = None
        self._host = None
        self._client = None
        self._event_bridge = None
        self._turn_bridge = None
        self._server = None
        self._is_hosting = False
        self._is_connected = False
        self._join_address = None

    @property
    def is_hosting(self) -> bool:
        return self._is_hosting

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def join_address(self) -> str:
        return self._join_address or ""

    # ------------------------------------------------------------------
    # Host mode (DM)
    # ------------------------------------------------------------------

    def host(self, port: int = 8765):
        """Start hosting a session on the given port.

        Creates a background event loop, starts the transport server, session
        host, and event bridges.

        :param port: TCP port to listen on.
        :type port: int
        """
        if self._is_hosting or self._is_connected:
            return

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(self._loop,),
            daemon=True,
        )
        self._thread.start()

        future = asyncio.run_coroutine_threadsafe(
            self._start_hosting(port), self._loop
        )
        future.add_done_callback(self._on_host_started)

    async def _start_hosting(self, port):
        from network.session_host import SessionHost
        from network.event_bridge import EventBridge, TurnBridge

        if self._transport_factory:
            self._server = self._transport_factory(port=port)
        else:
            from network.websocket_transport import WebSocketServer
            self._server = WebSocketServer(port=port)

        self._host = SessionHost(self.gamemaster, self._server)
        await self._host.start()

        # Start event bridges
        self._event_bridge = EventBridge(self._host, self.gamemaster)
        self._event_bridge.start()
        self._turn_bridge = TurnBridge(self._host, self.gamemaster)
        self._turn_bridge.start()

        if hasattr(self._server, "get_join_address"):
            self._join_address = self._server.get_join_address()
        else:
            self._join_address = f"localhost:{port}"

        self._is_hosting = True
        logger.info(f"Hosting session on {self._join_address}")

    def _on_host_started(self, future):
        try:
            future.result()
        except Exception as e:
            logger.error(f"Failed to start hosting: {e}")
            self.signals.connection_error.emit(str(e))

    def stop_hosting(self):
        """Stop the hosted session and shut down the background event loop."""
        if not self._is_hosting:
            return

        if self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self._stop_hosting(), self._loop
            )
            try:
                future.result(timeout=5.0)
            except Exception as e:
                logger.error(f"Error stopping host: {e}")

        self._shutdown_loop()
        self._is_hosting = False
        self.signals.disconnected.emit()

    async def _stop_hosting(self):
        if self._event_bridge:
            self._event_bridge.stop()
            self._event_bridge = None
        if self._turn_bridge:
            self._turn_bridge.stop()
            self._turn_bridge = None
        if self._host:
            await self._host.stop()
            self._host = None

    # ------------------------------------------------------------------
    # Client mode (Player)
    # ------------------------------------------------------------------

    def join(self, host_addr: str, port: int, player_name: str):
        """Connect to a remote session as a player.

        :param host_addr: The server hostname or IP address.
        :type host_addr: str
        :param port: The server port.
        :type port: int
        :param player_name: Display name for this player.
        :type player_name: str
        """
        if self._is_hosting or self._is_connected:
            return

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(self._loop,),
            daemon=True,
        )
        self._thread.start()

        future = asyncio.run_coroutine_threadsafe(
            self._start_joining(host_addr, port, player_name), self._loop
        )
        future.add_done_callback(self._on_join_done)

    async def _start_joining(self, host_addr, port, player_name):
        from network.session_client import SessionClient

        if self._transport_factory:
            transport = self._transport_factory(host=host_addr, port=port)
        else:
            from network.websocket_transport import WebSocketClient
            transport = WebSocketClient(host_addr, port)

        self._client = SessionClient(player_name, transport)
        await self._client.connect()

        # Register handlers for UI updates
        self._client.on(MessageType.FULL_STATE, self._on_full_state)
        self._client.on(MessageType.STATE_DELTA, self._on_state_delta)
        self._client.on(MessageType.ENTITY_CLAIMED, self._on_entity_claimed)
        self._client.on(MessageType.CHAT, self._on_chat)

        self._is_connected = True

        # Start listening in background
        asyncio.ensure_future(self._listen_loop())

    def _on_join_done(self, future):
        try:
            future.result()
            self.signals.connected.emit()
        except Exception as e:
            logger.error(f"Failed to join session: {e}")
            self.signals.connection_error.emit(str(e))

    async def _listen_loop(self):
        """Listen for messages until disconnected."""
        try:
            await self._client.listen()
        except Exception as e:
            logger.error(f"Listen loop error: {e}")
        finally:
            self._is_connected = False
            self.signals.disconnected.emit()

    def leave(self):
        """Disconnect from the remote session and shut down the background loop."""
        if not self._is_connected:
            return

        if self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self._disconnect_client(), self._loop
            )
            try:
                future.result(timeout=5.0)
            except Exception as e:
                logger.error(f"Error leaving session: {e}")

        self._shutdown_loop()
        self._is_connected = False
        self.signals.disconnected.emit()

    async def _disconnect_client(self):
        if self._client:
            await self._client.disconnect()
            self._client = None

    # ------------------------------------------------------------------
    # Shared operations
    # ------------------------------------------------------------------

    def send_chat(self, message: str):
        """Send a chat message (works in both host and client mode).

        :param message: The chat text to send.
        :type message: str
        """
        if self._client and self._is_connected and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._client.send_chat(message), self._loop
            )

    def claim_entity(self, entity_id: str):
        """Claim an entity (client mode only).

        :param entity_id: The unique identifier of the entity to claim.
        :type entity_id: str
        """
        if self._client and self._is_connected and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._client.claim_entity(entity_id), self._loop
            )

    # ------------------------------------------------------------------
    # Signal-emitting callbacks (called from async context)
    # ------------------------------------------------------------------

    def _on_full_state(self, msg):
        self.signals.state_updated.emit()

    def _on_state_delta(self, msg):
        self.signals.state_updated.emit()

    def _on_entity_claimed(self, msg):
        entity_id = msg.payload.get("entity_id", "")
        player_id = msg.payload.get("player_id", "")
        self.signals.entity_claimed.emit(entity_id, player_id)

    def _on_chat(self, msg):
        sender = msg.payload.get("sender", "")
        message = msg.payload.get("message", "")
        self.signals.chat_received.emit(sender, message)

    # ------------------------------------------------------------------
    # Event loop management
    # ------------------------------------------------------------------

    @staticmethod
    def _run_loop(loop):
        """Run the asyncio event loop in a background thread."""
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def _shutdown_loop(self):
        """Stop and close the background event loop."""
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=3.0)
            self._loop.close()
            self._loop = None
            self._thread = None

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
    #: Emitted when an ACTION_RESULT arrives (success, message).
    action_result_received = pyqtSignal(bool, str)
    #: Emitted when a TURN_CHANGE arrives (entity_name, round_number).
    turn_changed = pyqtSignal(str, int)
    #: Emitted after connection with the list of claimable entities.
    entities_available = pyqtSignal(list)
    #: Emitted when voice generation progress updates (character_id, completed, total).
    voice_progress = pyqtSignal(str, int, int)
    #: Emitted when all voice characters are generated.
    voice_all_complete = pyqtSignal()
    #: Emitted when another player's cursor moves (player_id, name, x, y, color).
    cursor_updated = pyqtSignal(str, str, float, float, str)
    #: Emitted when a draw stroke is received (player_id, points_json, color).
    draw_received = pyqtSignal(str, list, str)


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
        self._swarm_orchestrator = None
        self._swarm_worker = None
        self._intentional_disconnect = False
        self._session_password: str = ""
        self._use_tls: bool = True  # TLS enabled by default

    @property
    def is_hosting(self) -> bool:
        return self._is_hosting

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def join_address(self) -> str:
        return self._join_address or ""

    @property
    def claimed_entity_id(self) -> str:
        """Return the entity ID claimed by this client, or empty string."""
        if self._client:
            return self._client.claimed_entity_id or ""
        return ""

    # ------------------------------------------------------------------
    # Host mode (DM)
    # ------------------------------------------------------------------

    def host(self, port: int = 8765, password: str = "", use_tls: bool = True):
        """Start hosting a session on the given port.

        :param port: TCP port to listen on.
        :param password: Optional session password. Clients must provide
            this in their HELLO message to connect.
        :param use_tls: Whether to enable TLS encryption (default True).
            Uses a self-signed certificate generated per session.
        """
        self._session_password = password
        self._use_tls = use_tls
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
            # Enable TLS if possible
            ssl_ctx = None
            if self._use_tls:
                from network.tls_utils import create_self_signed_ssl_context
                ssl_ctx = create_self_signed_ssl_context()
            self._server = WebSocketServer(port=port, ssl_context=ssl_ctx)

        self._host = SessionHost(
            self.gamemaster, self._server,
            password=self._session_password,
        )
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

        # Register voice swarm handlers on the host
        self._host._message_handlers[MessageType.VOICE_CAPABILITY] = self._handle_voice_capability
        self._host._message_handlers[MessageType.VOICE_CHARACTER_PROGRESS] = self._handle_voice_progress
        self._host._message_handlers[MessageType.VOICE_CHARACTER_COMPLETE] = self._handle_voice_complete

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
        await asyncio.wait_for(self._client.connect(), timeout=10.0)

        # Register handlers for UI updates
        self._client.on(MessageType.FULL_STATE, self._on_full_state)
        self._client.on(MessageType.STATE_DELTA, self._on_state_delta)
        self._client.on(MessageType.ENTITY_CLAIMED, self._on_entity_claimed)
        self._client.on(MessageType.CHAT, self._on_chat)
        self._client.on(MessageType.ACTION_RESULT, self._on_action_result)
        self._client.on(MessageType.TURN_CHANGE, self._on_turn_change)
        self._client.on(MessageType.VOICE_CHARACTER_ASSIGN, self._on_voice_character_assign)
        self._client.on(MessageType.VOICE_CACHE_SYNC, self._on_voice_cache_sync)
        self._client.on(MessageType.CURSOR_UPDATE, self._on_cursor_update)
        self._client.on(MessageType.DRAW_STROKE, self._on_draw_stroke)

        self._is_connected = True

        # Start listening in background
        asyncio.ensure_future(self._listen_loop())

    def _on_join_done(self, future):
        try:
            future.result()
            self.signals.connected.emit()
            if self._client and self._client.available_entities:
                self.signals.entities_available.emit(self._client.available_entities)
        except Exception as e:
            logger.error(f"Failed to join session: {e}")
            self.signals.connection_error.emit(str(e))

    async def _listen_loop(self):
        """Listen for messages until disconnected, then auto-reconnect."""
        try:
            await self._client.listen()
        except Exception as e:
            logger.error(f"Listen loop error: {e}")

        self._is_connected = False
        self.signals.disconnected.emit()

        # Auto-reconnect with exponential backoff
        if self._client and not self._intentional_disconnect:
            await self._reconnect_loop()

    async def _reconnect_loop(self, max_attempts: int = 10):
        """Attempt to reconnect to the host with exponential backoff."""
        for attempt in range(max_attempts):
            backoff = min(2 ** attempt, 30)
            logger.info(
                f"Reconnect attempt {attempt + 1}/{max_attempts} "
                f"in {backoff}s..."
            )
            await asyncio.sleep(backoff)

            try:
                await self._client.reconnect()
                self._is_connected = True
                self.signals.connected.emit()
                logger.info("Reconnected successfully")
                # Re-enter listen loop
                await self._client.listen()
                # If listen returns, connection dropped again
                self._is_connected = False
                self.signals.disconnected.emit()
            except (ConnectionError, OSError, Exception) as exc:
                logger.warning(f"Reconnect failed: {exc}")
                continue

        logger.error(f"Reconnection failed after {max_attempts} attempts")
        self.signals.connection_error.emit(
            f"Reconnection failed after {max_attempts} attempts"
        )

    def leave(self):
        """Disconnect from the remote session and shut down the background loop."""
        if not self._is_connected:
            return
        self._intentional_disconnect = True

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
        elif self._host and self._is_hosting and self._loop:
            # Host broadcasts directly — no client connection to self
            from network.protocol import make_chat
            chat_msg = make_chat("DM", message)
            asyncio.run_coroutine_threadsafe(
                self._host.broadcast(chat_msg), self._loop
            )

    def send_message(self, msg) -> None:
        """Send an arbitrary protocol message to the session.

        Used for real-time collaboration messages (cursor updates, draw
        strokes) that bypass the typed send_chat / claim_entity helpers.

        :param msg: A :class:`~network.protocol.Message` to send.
        """
        if self._client and self._is_connected and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._client.conn.send(msg.to_json()), self._loop,
            )
        elif self._host and self._is_hosting and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._host.broadcast(msg), self._loop,
            )
            # Also show in local chat panel via signal
            self.signals.chat_received.emit("DM", message)

    def claim_entity(self, entity_id: str):
        """Claim an entity (client mode only).

        :param entity_id: The unique identifier of the entity to claim.
        :type entity_id: str
        """
        if self._client and self._is_connected and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._client.claim_entity(entity_id), self._loop
            )

    def request_action(self, action_type: str, params: dict):
        """Send an action request to the host (client mode only).

        :param action_type: Type of action (e.g. ``"move"``, ``"attack"``).
        :type action_type: str
        :param params: Action-specific parameters.
        :type params: dict
        """
        if self._client and self._is_connected and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._client.request_action(action_type, params), self._loop
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

    def _on_action_result(self, msg):
        success = msg.payload.get("success", False)
        result = msg.payload.get("result", {})
        if success:
            action = result.get("action", "action")
            if action == "attack":
                if result.get("hit"):
                    message = f"Attack hit for {result.get('damage', 0)} damage"
                else:
                    message = "Attack missed"
            elif action == "move":
                message = f"Moved to {result.get('to', '?')}"
            elif action == "end_turn":
                message = "Turn ended"
            else:
                message = f"{action} succeeded"
        else:
            message = result.get("message", "Action failed")
        self.signals.action_result_received.emit(success, message)

    def _on_turn_change(self, msg):
        entity_name = msg.payload.get("current_entity", "")
        round_number = msg.payload.get("round", 0)
        self.signals.turn_changed.emit(entity_name, round_number)

    def _on_cursor_update(self, msg):
        p = msg.payload
        self.signals.cursor_updated.emit(
            p.get("player_id", ""),
            p.get("player_name", ""),
            float(p.get("x", 0)),
            float(p.get("y", 0)),
            p.get("color", "#888888"),
        )

    def _on_draw_stroke(self, msg):
        p = msg.payload
        self.signals.draw_received.emit(
            p.get("player_id", ""),
            p.get("points", []),
            p.get("color", "#888888"),
        )

    # ------------------------------------------------------------------
    # Voice swarm — client-side callbacks
    # ------------------------------------------------------------------

    def _on_voice_character_assign(self, msg):
        """Client received a character assignment from the DM."""
        if self._swarm_worker is None:
            from network.voice.swarm_worker import SwarmWorker
            from core.voice.voice_engine import VoiceEngine
            self._swarm_worker = SwarmWorker(
                voice_engine=VoiceEngine.instance(),
                voice_cache=None,
                on_progress=self._worker_on_progress,
                on_complete=self._worker_on_complete,
            )
        self._swarm_worker.handle_character_assign(msg.payload)

    def _on_voice_cache_sync(self, msg):
        """Client received cached audio from the DM."""
        if self._swarm_worker:
            self._swarm_worker.handle_cache_sync(msg.payload)

    def _worker_on_progress(self, data):
        """Worker progress callback — sends to host."""
        if self._client and self._is_connected and self._loop:
            from network.voice.swarm_protocol import make_voice_character_progress
            msg = make_voice_character_progress(
                data["character_id"], data["completed"], data["total"],
            )
            asyncio.run_coroutine_threadsafe(
                self._client.conn.send(msg.to_json()), self._loop,
            )

    def _worker_on_complete(self, data):
        """Worker completion callback — sends to host."""
        if self._client and self._is_connected and self._loop:
            from network.voice.swarm_protocol import make_voice_character_complete
            msg = make_voice_character_complete(
                data["character_id"], data["entity_name"],
                data["results"], data.get("total_generation_time_ms", 0),
            )
            asyncio.run_coroutine_threadsafe(
                self._client.conn.send(msg.to_json()), self._loop,
            )

    # ------------------------------------------------------------------
    # Voice swarm — host-side handlers (async, called from host message loop)
    # ------------------------------------------------------------------

    async def _handle_voice_capability(self, player, msg):
        """Host receives capability report from a client."""
        if self._swarm_orchestrator is None:
            from network.voice.swarm_orchestrator import VoiceSwarmOrchestrator
            self._swarm_orchestrator = VoiceSwarmOrchestrator()
        self._swarm_orchestrator.register_worker(
            player.player_id, player.player_name, msg.payload,
        )

    async def _handle_voice_progress(self, player, msg):
        """Host receives progress update from a worker."""
        if self._swarm_orchestrator:
            self._swarm_orchestrator.handle_progress(player.player_id, msg.payload)
        char_id = msg.payload.get("character_id", "")
        completed = msg.payload.get("completed", 0)
        total = msg.payload.get("total", 0)
        self.signals.voice_progress.emit(char_id, completed, total)

    async def _handle_voice_complete(self, player, msg):
        """Host receives completed character from a worker."""
        if self._swarm_orchestrator:
            sync_data = self._swarm_orchestrator.handle_character_complete(
                player.player_id, msg.payload,
            )
            # Broadcast cache sync to all clients
            if sync_data and self._host:
                from network.voice.swarm_protocol import make_voice_cache_sync
                sync_msg = make_voice_cache_sync(
                    sync_data["character_id"],
                    sync_data["entity_name"],
                    sync_data["results"],
                )
                await self._host.broadcast(sync_msg)

    # ------------------------------------------------------------------
    # Voice swarm — public API
    # ------------------------------------------------------------------

    def start_voice_swarm(self, voiced_entities: list) -> None:
        """Start distributed voice generation (host only).

        :param voiced_entities: List of entities with voice profiles.
        """
        if not self._is_hosting or not self._swarm_orchestrator:
            return
        assignments = self._swarm_orchestrator.start_generation(voiced_entities)
        # Send assignments to workers
        if self._host and self._loop:
            for player_id, char_ids in assignments.items():
                player = self._host.players.get(player_id)
                if not player:
                    continue
                for char_id in char_ids:
                    char_work = self._swarm_orchestrator.get_character_work(char_id)
                    if not char_work:
                        continue
                    from network.voice.swarm_protocol import make_voice_character_assign
                    msg = make_voice_character_assign(
                        char_work.character_id,
                        char_work.entity_name,
                        char_work.voice_seed_path,
                        char_work.params,
                        char_work.lines,
                    )
                    asyncio.run_coroutine_threadsafe(
                        player.conn.send(msg.to_json()), self._loop,
                    )

    def get_voice_swarm_stats(self) -> dict:
        """Get voice generation stats (host only)."""
        if self._swarm_orchestrator:
            return self._swarm_orchestrator.get_stats()
        return {}

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

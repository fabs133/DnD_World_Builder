"""
Session Client
==============

Client-side multiplayer session manager.

Connects to a :class:`~network.session_host.SessionHost`, performs the
HELLO/WELCOME handshake, then listens for state updates, entity claims,
and chat messages. Players send actions through this client.
"""

import asyncio
import logging
from network.transport import TransportClient
from network.protocol import (
    Message, MessageType,
    make_hello, make_disconnect, make_claim_entity,
    make_chat, make_action_request,
)
from network.reliable_channel import ReliableChannel

logger = logging.getLogger(__name__)


class SessionClient:
    """Manages a multiplayer session from the player (client) side.

    Accepts a :class:`~network.transport.TransportClient` (real WebSocket
    or :class:`~network.transport.InMemoryClient` for testing).

    :param player_name: Display name for this player.
    :type player_name: str
    :param transport: The transport client used to connect.
    :type transport: ~network.transport.TransportClient
    """

    def __init__(self, player_name, transport: TransportClient):
        self.player_name = player_name
        self.transport = transport
        self.conn = None
        self.channel: ReliableChannel | None = None
        self.player_id = None
        self.session_id = None
        self.color = "#888888"
        self.available_entities = []
        self.claimed_entity_id = None
        self.world_state = None
        self.turn_state = None
        self._handlers = {}  # MessageType -> [callable]
        self._host_addr = ""
        self._host_port = 0

    def on(self, msg_type, handler):
        """Register a callback for a specific message type.

        :param msg_type: The message type to listen for.
        :type msg_type: ~network.protocol.MessageType
        :param handler: Callable receiving a :class:`~network.protocol.Message`.
        :type handler: callable
        """
        self._handlers.setdefault(msg_type, []).append(handler)

    async def connect(self):
        """Connect to the server and perform the HELLO/WELCOME handshake.

        After a successful handshake, :attr:`session_id`, :attr:`player_id`,
        and :attr:`available_entities` are populated.

        :raises ConnectionError: If the server rejects the connection
            (version mismatch or protocol error).
        """
        self.conn = await self.transport.connect()

        hello = make_hello(self.player_name)
        await self.conn.send(hello.to_json())

        raw = await self.conn.recv()
        msg = Message.from_json(raw)

        if msg.type == MessageType.ERROR:
            raise ConnectionError(f"Server rejected: {msg.payload.get('message')}")

        if msg.type != MessageType.WELCOME:
            raise ConnectionError(f"Expected WELCOME, got {msg.type}")

        self.session_id = msg.payload.get("session_id")
        self.player_id = msg.payload.get("player_id")
        self.color = msg.payload.get("color", "#888888")
        self.available_entities = msg.payload.get("entities", [])

        # Create reliable channel for the post-handshake communication
        self.channel = ReliableChannel(self.conn, channel_id=self.player_id or "client")
        self.channel.on_message = self._dispatch_message
        self.channel.on_disconnect = self._on_channel_disconnect

        logger.info(f"Connected as {self.player_id} to session {self.session_id}")

    def _dispatch_message(self, msg: Message) -> None:
        """Route a message from the channel to internal state + handlers."""
        if msg.type == MessageType.FULL_STATE:
            self.world_state = msg.payload.get("world")
            self.turn_state = msg.payload.get("turn")
        elif msg.type == MessageType.STATE_DELTA:
            if self.world_state:
                from network.sync import apply_delta
                self.world_state = apply_delta(
                    self.world_state,
                    msg.payload.get("changes", []),
                )
        elif msg.type == MessageType.ENTITY_CLAIMED:
            if msg.payload.get("player_id") == self.player_id:
                self.claimed_entity_id = msg.payload.get("entity_id")

        for handler in self._handlers.get(msg.type, []):
            handler(msg)

    def _on_channel_disconnect(self) -> None:
        """Called by the channel when the connection is lost."""
        logger.warning(f"Channel disconnected for {self.player_id}")

    async def listen(self):
        """Start the reliable channel's listen + heartbeat loops.

        Call after :meth:`connect`. The channel handles heartbeat,
        ACK processing, and deduplication internally. Application-level
        messages are dispatched via :meth:`on` handlers.
        """
        if self.channel:
            await self.channel.start()
            # Wait for the listen task to complete (connection dropped)
            if self.channel._listen_task:
                try:
                    await self.channel._listen_task
                except (asyncio.CancelledError, Exception):
                    pass

    async def claim_entity(self, entity_id):
        """Send a CLAIM_ENTITY request to the host."""
        msg = make_claim_entity(entity_id)
        if self.channel:
            await self.channel.fire(msg)
        elif self.conn:
            await self.conn.send(msg.to_json())

    async def send_chat(self, message):
        """Send a CHAT message to the session."""
        msg = make_chat(self.player_name, message)
        if self.channel:
            await self.channel.fire(msg)
        elif self.conn:
            await self.conn.send(msg.to_json())

    async def request_action(self, action_type, params):
        """Send an ACTION_REQUEST to the host."""
        msg = make_action_request(action_type, params)
        if self.channel:
            await self.channel.fire(msg)
        elif self.conn:
            await self.conn.send(msg.to_json())

    async def reconnect(self):
        """Reconnect to the host after a connection drop.

        Performs a fresh HELLO/WELCOME handshake. The host will send a
        new FULL_STATE to resync the client.
        """
        if self.channel:
            await self.channel.stop()
            self.channel = None
        if self.conn and not self.conn.closed:
            try:
                await self.conn.close()
            except Exception:
                pass
        self.conn = None
        # Re-run the full connection flow
        await self.connect()

    async def disconnect(self):
        """Send a DISCONNECT message and close the connection."""
        if self.channel:
            await self.channel.fire(make_disconnect())
            await self.channel.stop()
        if self.conn and not self.conn.closed:
            try:
                await self.conn.close()
            except Exception:
                pass

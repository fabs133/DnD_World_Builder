"""
Session Client
==============

Client-side multiplayer session manager.

Connects to a :class:`~network.session_host.SessionHost`, performs the
HELLO/WELCOME handshake, then listens for state updates, entity claims,
and chat messages. Players send actions through this client.
"""

import logging
from network.transport import TransportClient
from network.protocol import (
    Message, MessageType,
    make_hello, make_disconnect, make_claim_entity,
    make_chat, make_action_request,
)

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
        self.player_id = None
        self.session_id = None
        self.available_entities = []
        self.claimed_entity_id = None
        self.world_state = None
        self.turn_state = None
        self._handlers = {}  # MessageType -> [callable]

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
        self.available_entities = msg.payload.get("entities", [])

        logger.info(f"Connected as {self.player_id} to session {self.session_id}")

    async def listen(self):
        """Receive and dispatch messages in a loop.

        Call after :meth:`connect`. Updates :attr:`world_state` and
        :attr:`turn_state` from FULL_STATE and STATE_DELTA messages,
        and fires registered callbacks via :meth:`on`.
        """
        while self.conn and not self.conn.closed:
            try:
                raw = await self.conn.recv()
                msg = Message.from_json(raw)
            except (ValueError, ConnectionError):
                break

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

    async def claim_entity(self, entity_id):
        """Send a CLAIM_ENTITY request to the host.

        :param entity_id: Name/ID of the entity to claim.
        :type entity_id: str
        """
        msg = make_claim_entity(entity_id)
        await self.conn.send(msg.to_json())

    async def send_chat(self, message):
        """Send a CHAT message to the session.

        :param message: Chat text to send.
        :type message: str
        """
        msg = make_chat(self.player_name, message)
        await self.conn.send(msg.to_json())

    async def request_action(self, action_type, params):
        """Send an ACTION_REQUEST to the host.

        :param action_type: Type of action (e.g. ``"move"``).
        :type action_type: str
        :param params: Action-specific parameters.
        :type params: dict
        """
        msg = make_action_request(action_type, params)
        await self.conn.send(msg.to_json())

    async def disconnect(self):
        """Send a DISCONNECT message and close the connection."""
        if self.conn and not self.conn.closed:
            msg = make_disconnect()
            await self.conn.send(msg.to_json())
            await self.conn.close()

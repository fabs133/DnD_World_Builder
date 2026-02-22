"""
Session Host
============

Server-side multiplayer session manager.

Handles the full lifecycle of a hosted session: accepting connections,
performing the HELLO/WELCOME handshake, managing entity claims, relaying
chat, and dispatching gameplay actions. The :class:`Gamemaster` is the
authoritative source of truth for all game state.
"""

import asyncio
import uuid
import logging
from network.transport import TransportServer, TransportConnection
from network.protocol import (
    Message, MessageType, PROTOCOL_VERSION,
    make_welcome, make_error, make_entity_claimed,
    make_full_state, make_chat, ErrorCode,
)
from network.sync import serialize_world, serialize_entity

logger = logging.getLogger(__name__)


class ConnectedPlayer:
    """Tracks a connected player's state.

    :param player_id: Unique identifier assigned on connection.
    :type player_id: str
    :param player_name: Display name from the HELLO message.
    :type player_name: str
    :param conn: The player's transport connection.
    :type conn: ~network.transport.TransportConnection
    """

    def __init__(self, player_id, player_name, conn):
        self.player_id = player_id
        self.player_name = player_name
        self.conn = conn
        self.claimed_entity_id = None


class SessionHost:
    """Manages a multiplayer session from the DM (host) side.

    Accepts a :class:`~network.transport.TransportServer` (real WebSocket
    or :class:`~network.transport.InMemoryServer` for testing). All game
    logic is delegated to the :class:`~models.game_master.Gamemaster`
    which remains the source of truth.

    :param gamemaster: The authoritative game state holder.
    :param transport: The transport server to accept connections on.
    :type transport: ~network.transport.TransportServer
    """

    def __init__(self, gamemaster, transport: TransportServer):
        self.gamemaster = gamemaster
        self.transport = transport
        self.session_id = str(uuid.uuid4())[:8]
        self.players = {}  # player_id -> ConnectedPlayer
        self._entity_claims = {}  # entity_id -> player_id
        self._seq = 0
        self._message_handlers = {
            MessageType.HELLO: self._handle_hello,
            MessageType.CLAIM_ENTITY: self._handle_claim_entity,
            MessageType.ACTION_REQUEST: self._handle_action_request,
            MessageType.CHAT: self._handle_chat,
            MessageType.DISCONNECT: self._handle_disconnect,
        }

    async def start(self):
        """Start the session and begin accepting connections."""
        self.transport.on_connection(self._on_new_connection)
        await self.transport.start()
        logger.info(f"Session {self.session_id} started")

    async def stop(self):
        """Stop the session and disconnect all players."""
        await self.transport.stop()
        logger.info(f"Session {self.session_id} stopped")

    async def _on_new_connection(self, conn: TransportConnection):
        """Handle a new client connection.

        Performs the HELLO/WELCOME handshake, sends a FULL_STATE snapshot,
        then enters the message loop.

        :param conn: The newly connected transport endpoint.
        :type conn: ~network.transport.TransportConnection
        """
        try:
            raw = await asyncio.wait_for(conn.recv(), timeout=10.0)
            msg = Message.from_json(raw)
        except (asyncio.TimeoutError, ValueError) as e:
            error = make_error(ErrorCode.INVALID_MESSAGE, str(e))
            await conn.send(error.to_json())
            await conn.close()
            return

        if msg.type != MessageType.HELLO:
            error = make_error(ErrorCode.INVALID_MESSAGE, "Expected HELLO")
            await conn.send(error.to_json())
            await conn.close()
            return

        client_version = msg.payload.get("version", "")
        if client_version != PROTOCOL_VERSION:
            error = make_error(
                ErrorCode.VERSION_MISMATCH,
                f"Server: {PROTOCOL_VERSION}, Client: {client_version}",
            )
            await conn.send(error.to_json())
            await conn.close()
            return

        player_name = msg.payload.get("player_name", "Unknown")
        player_id = str(uuid.uuid4())[:8]
        player = ConnectedPlayer(player_id, player_name, conn)
        self.players[player_id] = player

        # Send WELCOME
        entity_summaries = [serialize_entity(e) for e in self.gamemaster.game_entities]
        welcome = make_welcome(self.session_id, player_id, entity_summaries)
        await conn.send(welcome.to_json())

        # Send FULL_STATE
        world_data = serialize_world(self.gamemaster.world)
        turn_data = {
            "current_turn": self.gamemaster.turn_system.current_turn,
            "round_number": self.gamemaster.turn_system.round_number,
        }
        full_state = make_full_state(world_data, entity_summaries, turn_data)
        await conn.send(full_state.to_json())

        logger.info(f"Player '{player_name}' ({player_id}) connected")

        # Message loop
        await self._message_loop(player, conn)

    async def _message_loop(self, player, conn):
        """Read and dispatch messages from a client until disconnect or error.

        :param player: The connected player.
        :type player: ConnectedPlayer
        :param conn: The player's transport connection.
        :type conn: ~network.transport.TransportConnection
        """
        while not conn.closed:
            try:
                raw = await conn.recv()
                msg = Message.from_json(raw)
            except (ValueError, ConnectionError):
                break

            handler = self._message_handlers.get(msg.type)
            if handler:
                await handler(player, msg)
            else:
                error = make_error(
                    ErrorCode.INVALID_MESSAGE,
                    f"Unexpected message type: {msg.type}",
                )
                await conn.send(error.to_json())

        self.players.pop(player.player_id, None)
        logger.info(f"Player '{player.player_name}' disconnected")

    async def broadcast(self, msg, exclude=None):
        """Send a message to all connected players.

        :param msg: The message to broadcast.
        :type msg: ~network.protocol.Message
        :param exclude: Player ID to skip (e.g. the sender).
        :type exclude: str or None
        """
        data = msg.to_json()
        for pid, player in list(self.players.items()):
            if pid != exclude:
                try:
                    await player.conn.send(data)
                except ConnectionError:
                    pass

    async def _handle_hello(self, player, msg):
        """No-op: HELLO is already handled during the handshake."""
        pass

    async def _handle_claim_entity(self, player, msg):
        """Process a CLAIM_ENTITY request.

        Validates the entity exists and is unclaimed, then broadcasts
        ENTITY_CLAIMED to all players. Sends an ERROR on failure.
        """
        entity_id = msg.payload.get("entity_id")

        if entity_id in self._entity_claims:
            error = make_error(
                ErrorCode.ENTITY_ALREADY_CLAIMED,
                f"Entity '{entity_id}' already claimed",
            )
            await player.conn.send(error.to_json())
            return

        entity = next(
            (e for e in self.gamemaster.game_entities if e.name == entity_id),
            None,
        )
        if not entity:
            error = make_error(
                ErrorCode.UNKNOWN_ENTITY,
                f"No entity named '{entity_id}'",
            )
            await player.conn.send(error.to_json())
            return

        self._entity_claims[entity_id] = player.player_id
        player.claimed_entity_id = entity_id

        claimed = make_entity_claimed(entity_id, player.player_id)
        await self.broadcast(claimed)

    async def _handle_action_request(self, player, msg):
        """Process an ACTION_REQUEST. Stub for future gameplay phase."""
        pass

    async def _handle_chat(self, player, msg):
        """Broadcast a CHAT message to all connected players."""
        chat = make_chat(player.player_name, msg.payload.get("message", ""))
        await self.broadcast(chat)

    async def _handle_disconnect(self, player, msg):
        """Close the connection for a disconnecting player."""
        await player.conn.close()

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
import time
import uuid
import logging
from network.transport import TransportServer, TransportConnection
from network.protocol import (
    Message, MessageType, PROTOCOL_VERSION, CRITICAL_TYPES,
    make_welcome, make_error, make_entity_claimed,
    make_full_state, make_action_result, make_chat, ErrorCode,
    make_cursor_update, make_draw_stroke,
)
from network.reliable_channel import ReliableChannel
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

    def __init__(self, player_id, player_name, conn, color="#888888"):
        self.player_id = player_id
        self.player_name = player_name
        self.conn = conn
        self.claimed_entity_id = None
        self.color = color
        self.channel: ReliableChannel | None = None


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

    # Fixed color palette for player cursor/draw identification.
    _PLAYER_COLORS = [
        "#e74c3c", "#3498db", "#2ecc71", "#f39c12",
        "#9b59b6", "#1abc9c", "#e67e22", "#e91e63",
    ]

    def __init__(self, gamemaster, transport: TransportServer, password: str = ""):
        self.gamemaster = gamemaster
        self.transport = transport
        self.session_id = str(uuid.uuid4())[:8]
        self._password = password  # empty = no password required
        self.players = {}  # player_id -> ConnectedPlayer
        self._entity_claims = {}  # entity_id -> player_id
        self._entity_index = self._build_entity_index()
        self._seq = 0
        self._active_draws: dict[str, dict] = {}  # stroke_id -> {payload, expires}
        self._color_index = 0
        self._message_handlers = {
            MessageType.HELLO: self._handle_hello,
            MessageType.CLAIM_ENTITY: self._handle_claim_entity,
            MessageType.ACTION_REQUEST: self._handle_action_request,
            MessageType.CHAT: self._handle_chat,
            MessageType.DISCONNECT: self._handle_disconnect,
            MessageType.CURSOR_UPDATE: self._handle_cursor_update,
            MessageType.DRAW_STROKE: self._handle_draw_stroke,
        }

    def _build_entity_index(self) -> dict:
        """Build a name→entity lookup dict, warning on duplicates."""
        index = {}
        for e in self.gamemaster.game_entities:
            if e.name in index:
                logger.warning(f"Duplicate entity name: {e.name}")
            index[e.name] = e
        return index

    async def start(self):
        """Start the session and begin accepting connections."""
        self.transport.on_connection(self._on_new_connection)
        await self.transport.start()
        logger.info(f"Session {self.session_id} started")

    async def stop(self):
        """Stop the session and disconnect all players."""
        # Notify all players before shutdown
        goodbye = make_error(ErrorCode.INVALID_MESSAGE, "Host is shutting down")
        await self.broadcast(goodbye)
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

        # Password check (if host has a password set)
        if self._password:
            client_password = msg.payload.get("password", "")
            if client_password != self._password:
                error = make_error(
                    ErrorCode.WRONG_PASSWORD,
                    "Incorrect session password",
                )
                await conn.send(error.to_json())
                await conn.close()
                logger.warning(
                    f"Rejected connection from "
                    f"'{msg.payload.get('player_name', '?')}': wrong password"
                )
                return

        player_name = msg.payload.get("player_name", "Unknown")
        player_id = str(uuid.uuid4())[:8]
        color = self._PLAYER_COLORS[self._color_index % len(self._PLAYER_COLORS)]
        self._color_index += 1
        player = ConnectedPlayer(player_id, player_name, conn, color=color)
        self.players[player_id] = player

        # Send WELCOME (includes assigned color for cursor/draw)
        entity_summaries = [serialize_entity(e) for e in self.gamemaster.game_entities]
        welcome = make_welcome(self.session_id, player_id, entity_summaries)
        welcome.payload["color"] = color
        await conn.send(welcome.to_json())

        # Send FULL_STATE
        world_data = serialize_world(self.gamemaster.world)
        turn_data = {
            "current_turn": self.gamemaster.turn_system.current_turn,
            "round_number": self.gamemaster.turn_system.round_number,
        }
        full_state = make_full_state(world_data, entity_summaries, turn_data)
        await conn.send(full_state.to_json())

        # Send active (non-expired) draw strokes so late joiners see them
        self._prune_expired_draws()
        for stroke_data in self._active_draws.values():
            draw_msg = Message(
                type=MessageType.DRAW_STROKE,
                payload=stroke_data["payload"],
            )
            await conn.send(draw_msg.to_json())

        logger.info(f"Player '{player_name}' ({player_id}) connected (color: {color})")

        # Create reliable channel for this player
        channel = ReliableChannel(conn, channel_id=player_id)
        player.channel = channel

        def _on_player_message(msg: Message):
            handler = self._message_handlers.get(msg.type)
            if handler:
                asyncio.ensure_future(handler(player, msg))
            else:
                logger.warning(f"Unhandled message type from {player_id}: {msg.type}")

        def _on_player_disconnect():
            self.players.pop(player_id, None)
            logger.info(f"Player '{player_name}' disconnected (channel lost)")

        channel.on_message = _on_player_message
        channel.on_disconnect = _on_player_disconnect

        # Start the channel (listen + heartbeat) and wait until it ends
        await channel.start()
        # Wait for channel to die (listen_task completes when connection drops)
        if channel._listen_task:
            try:
                await channel._listen_task
            except (asyncio.CancelledError, Exception):
                pass

        # Cleanup
        self.players.pop(player_id, None)
        logger.info(f"Player '{player_name}' disconnected")

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

        Uses the player's :class:`ReliableChannel` when available.
        Critical messages are sent via ``request()`` (with ACK/retry);
        non-critical messages use ``fire()`` (best-effort).
        Players that fail to receive are automatically evicted.

        :param msg: The message to broadcast.
        :type msg: ~network.protocol.Message
        :param exclude: Player ID to skip (e.g. the sender).
        :type exclude: str or None
        """
        to_remove = []
        for pid, player in list(self.players.items()):
            if pid == exclude:
                continue
            if player.channel and player.channel.alive:
                if msg.type in CRITICAL_TYPES:
                    ok = await player.channel.request(msg)
                else:
                    ok = await player.channel.fire(msg)
                if not ok:
                    to_remove.append(pid)
            else:
                # Fallback for players without a channel (shouldn't happen)
                try:
                    await player.conn.send(msg.to_json())
                except ConnectionError:
                    to_remove.append(pid)

        for pid in to_remove:
            player = self.players.pop(pid, None)
            if player:
                logger.info(f"Evicted unreachable player '{player.player_name}' ({pid})")

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

        entity = self._entity_index.get(entity_id)
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
        """Process an ACTION_REQUEST from a player.

        Validates:
        1. Player has a claimed entity.
        2. The claimed entity matches ``_entity_claims``.
        3. It is that entity's turn.
        4. The action itself is valid.

        On success the action is executed directly on the entity, an
        ``ACTION_RESULT(success=True)`` is sent to the requesting player,
        and the :class:`~network.event_bridge.EventBridge` (if attached)
        will automatically broadcast the resulting ``STATE_DELTA``.
        """
        action_type = msg.payload.get("action_type", "").upper()
        params = msg.payload.get("params", {})

        # 1. Player must have a claimed entity
        entity_id = player.claimed_entity_id
        if not entity_id:
            error = make_error(
                ErrorCode.UNKNOWN_ENTITY,
                "You have not claimed an entity",
            )
            await player.conn.send(error.to_json())
            return

        # 2. Verify ownership via _entity_claims
        if self._entity_claims.get(entity_id) != player.player_id:
            error = make_error(
                ErrorCode.INVALID_ACTION,
                f"You do not own entity '{entity_id}'",
            )
            await player.conn.send(error.to_json())
            return

        # 3. Look up the entity object
        entity = self._entity_index.get(entity_id)
        if not entity:
            error = make_error(
                ErrorCode.UNKNOWN_ENTITY,
                f"Entity '{entity_id}' not found in game",
            )
            await player.conn.send(error.to_json())
            return

        # 4. Check it is this entity's turn
        ts = self.gamemaster.turn_system
        if not ts.entities:
            error = make_error(
                ErrorCode.INVALID_ACTION,
                "No turn order established",
            )
            await player.conn.send(error.to_json())
            return
        if ts.entities[ts.current_turn].name != entity_id:
            current_name = ts.entities[ts.current_turn].name
            error = make_error(
                ErrorCode.NOT_YOUR_TURN,
                f"It is {current_name}'s turn, not {entity_id}'s",
            )
            await player.conn.send(error.to_json())
            return

        # 5. Build the action object
        action = self._build_action(action_type, params, entity)
        if action is None:
            error = make_error(
                ErrorCode.INVALID_ACTION,
                f"Unknown action type: {action_type}",
            )
            await player.conn.send(error.to_json())
            return

        # 6. Validate and execute
        from models.flow.action.action_validator import ActionValidator

        if not ActionValidator.validate(action, None):
            error = make_error(
                ErrorCode.INVALID_ACTION,
                f"Action validation failed for {action_type}",
            )
            await player.conn.send(error.to_json())
            return

        try:
            result_data = action.execute(None) or {}
        except Exception as exc:
            error = make_error(
                ErrorCode.INVALID_ACTION,
                f"Action execution failed: {exc}",
            )
            await player.conn.send(error.to_json())
            return

        # 7. Advance turn if END_TURN action
        if action_type in ("END_TURN", "ENDTURN", "END"):
            ts = self.gamemaster.turn_system
            ts.current_turn = (ts.current_turn + 1) % len(ts.entities)
            if ts.current_turn == 0:
                ts.round_number = getattr(ts, "round_number", 1) + 1

        # 8. Send success result to the requesting player
        result_msg = make_action_result(
            success=True,
            result=result_data,
            state_delta=[],
        )
        await player.conn.send(result_msg.to_json())

        logger.info(
            f"Player '{player.player_name}' executed {action_type} "
            f"for entity '{entity_id}'"
        )

    def _build_action(self, action_type, params, actor):
        """Construct an Action object from network parameters.

        Returns ``None`` if the action type is unknown.
        """
        from core.engine.actions.attack_action import AttackAction
        from core.engine.actions.move_action import MoveAction
        from core.engine.actions.end_turn_action import EndTurnAction

        if action_type == "ATTACK":
            target_name = params.get("target")
            target = self._entity_index.get(target_name)
            if target is None:
                return None
            return AttackAction(actor, target)

        if action_type == "MOVE":
            position = params.get("position")
            if not position or len(position) != 2:
                return None
            return MoveAction(
                actor,
                tuple(position),
                world_tile_manager=self.gamemaster.world_tile_manager,
            )

        if action_type in ("END_TURN", "ENDTURN", "END"):
            return EndTurnAction(actor)

        return None

    async def _handle_chat(self, player, msg):
        """Broadcast a CHAT message to all connected players."""
        chat = make_chat(player.player_name, msg.payload.get("message", ""))
        await self.broadcast(chat)

    async def _handle_cursor_update(self, player, msg):
        """Relay a cursor position update to all other players."""
        # Inject the player's server-assigned color and identity
        msg.payload["player_id"] = player.player_id
        msg.payload["player_name"] = player.player_name
        msg.payload["color"] = player.color
        await self.broadcast(msg, exclude=player.player_id)

    async def _handle_draw_stroke(self, player, msg):
        """Relay a draw stroke to all other players and store for late joiners."""
        msg.payload["player_id"] = player.player_id
        msg.payload["color"] = player.color

        # Store with expiry for late-joining players
        stroke_id = f"{player.player_id}_{self._seq}"
        self._active_draws[stroke_id] = {
            "payload": dict(msg.payload),
            "expires": time.time() + 15.0,
        }
        self._seq += 1
        self._prune_expired_draws()

        await self.broadcast(msg, exclude=player.player_id)

    def _prune_expired_draws(self) -> None:
        """Remove draw strokes that have passed their expiry time."""
        now = time.time()
        expired = [k for k, v in self._active_draws.items() if v["expires"] <= now]
        for k in expired:
            del self._active_draws[k]

    async def _handle_disconnect(self, player, msg):
        """Close the connection for a disconnecting player."""
        await player.conn.close()

"""
Multiplayer Protocol
====================

Defines the wire protocol for DM-to-player communication.

All messages are serialized as JSON strings. The protocol is versioned
(see :data:`PROTOCOL_VERSION`) so clients and servers can detect
incompatible changes.

Message Types
-------------

The 12 message types cover the full session lifecycle:

- **Handshake**: HELLO, WELCOME
- **Entity ownership**: CLAIM_ENTITY, ENTITY_CLAIMED
- **State synchronization**: FULL_STATE, STATE_DELTA
- **Gameplay**: ACTION_REQUEST, ACTION_RESULT, TURN_CHANGE
- **Communication**: CHAT
- **Control**: ERROR, DISCONNECT
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum


class MessageType(str, Enum):
    """Enumeration of all supported network message types."""

    HELLO = "HELLO"
    WELCOME = "WELCOME"
    CLAIM_ENTITY = "CLAIM_ENTITY"
    ENTITY_CLAIMED = "ENTITY_CLAIMED"
    FULL_STATE = "FULL_STATE"
    STATE_DELTA = "STATE_DELTA"
    ACTION_REQUEST = "ACTION_REQUEST"
    ACTION_RESULT = "ACTION_RESULT"
    TURN_CHANGE = "TURN_CHANGE"
    CHAT = "CHAT"
    ERROR = "ERROR"
    DISCONNECT = "DISCONNECT"
    # Real-time collaboration messages
    CURSOR_UPDATE = "CURSOR_UPDATE"
    DRAW_STROKE = "DRAW_STROKE"
    # Reliability / heartbeat
    PING = "PING"
    PONG = "PONG"
    ACK = "ACK"
    # Voice swarm messages
    VOICE_CAPABILITY = "VOICE_CAPABILITY"
    VOICE_CHARACTER_ASSIGN = "VOICE_CHARACTER_ASSIGN"
    VOICE_CHARACTER_PROGRESS = "VOICE_CHARACTER_PROGRESS"
    VOICE_CHARACTER_COMPLETE = "VOICE_CHARACTER_COMPLETE"
    VOICE_CACHE_SYNC = "VOICE_CACHE_SYNC"


class ErrorCode(str, Enum):
    """Standard error codes sent in ERROR messages."""

    INVALID_MESSAGE = "INVALID_MESSAGE"
    NOT_YOUR_TURN = "NOT_YOUR_TURN"
    ENTITY_ALREADY_CLAIMED = "ENTITY_ALREADY_CLAIMED"
    UNKNOWN_ENTITY = "UNKNOWN_ENTITY"
    INVALID_ACTION = "INVALID_ACTION"
    VERSION_MISMATCH = "VERSION_MISMATCH"
    WRONG_PASSWORD = "WRONG_PASSWORD"


PROTOCOL_VERSION = "1.0"
"""Current protocol version string, checked during the HELLO/WELCOME handshake."""


@dataclass
class Message:
    """A single protocol message exchanged between host and client.

    :param type: The message type.
    :type type: MessageType
    :param payload: Arbitrary message data (varies per type).
    :type payload: dict
    :param seq: Sequence number for ordering.
    :type seq: int
    :param timestamp: ISO-8601 UTC timestamp, auto-set if empty.
    :type timestamp: str
    """

    type: MessageType
    payload: dict = field(default_factory=dict)
    seq: int = 0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if isinstance(self.type, str):
            self.type = MessageType(self.type)

    def to_json(self) -> str:
        """Serialize this message to a JSON string.

        :return: JSON representation of the message.
        :rtype: str
        """
        return json.dumps({
            "type": self.type.value,
            "seq": self.seq,
            "timestamp": self.timestamp,
            "payload": self.payload,
        })

    @classmethod
    def from_json(cls, data: str) -> "Message":
        """Deserialize a JSON string into a Message.

        :param data: JSON string to parse.
        :type data: str
        :return: The deserialized message.
        :rtype: Message
        :raises ValueError: If the JSON is invalid or the message type is unknown.
        """
        try:
            obj = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

        if "type" not in obj:
            raise ValueError("Message missing 'type' field")

        try:
            msg_type = MessageType(obj["type"])
        except ValueError:
            raise ValueError(f"Unknown message type: {obj['type']}")

        return cls(
            type=msg_type,
            payload=obj.get("payload", {}),
            seq=obj.get("seq", 0),
            timestamp=obj.get("timestamp", ""),
        )


# --- Factory functions ---

def make_hello(player_name: str, password: str = "") -> Message:
    """Create a HELLO handshake message.

    :param player_name: The connecting player's display name.
    :param password: Optional session password set by the host.
    :return: A HELLO message containing the player name, version, and password.
    """
    payload = {
        "player_name": player_name,
        "version": PROTOCOL_VERSION,
    }
    if password:
        payload["password"] = password
    return Message(type=MessageType.HELLO, payload=payload)


def make_welcome(session_id: str, player_id: str, entities: list) -> Message:
    """Create a WELCOME response to a successful handshake.

    :param session_id: The session the player has joined.
    :type session_id: str
    :param player_id: Unique identifier assigned to the player.
    :type player_id: str
    :param entities: List of entity summary dicts available for claiming.
    :type entities: list[dict]
    :return: A WELCOME message.
    :rtype: Message
    """
    return Message(type=MessageType.WELCOME, payload={
        "session_id": session_id,
        "player_id": player_id,
        "entities": entities,
    })


def make_error(code: ErrorCode, message: str) -> Message:
    """Create an ERROR message.

    :param code: The error code.
    :type code: ErrorCode
    :param message: Human-readable error description.
    :type message: str
    :return: An ERROR message.
    :rtype: Message
    """
    return Message(type=MessageType.ERROR, payload={
        "code": code.value,
        "message": message,
    })


def make_chat(sender: str, message: str) -> Message:
    """Create a CHAT message.

    :param sender: Display name of the sender.
    :type sender: str
    :param message: Chat text.
    :type message: str
    :return: A CHAT message.
    :rtype: Message
    """
    return Message(type=MessageType.CHAT, payload={
        "sender": sender,
        "message": message,
    })


def make_claim_entity(entity_id: str) -> Message:
    """Create a CLAIM_ENTITY request.

    :param entity_id: Name/ID of the entity the player wants to control.
    :type entity_id: str
    :return: A CLAIM_ENTITY message.
    :rtype: Message
    """
    return Message(type=MessageType.CLAIM_ENTITY, payload={
        "entity_id": entity_id,
    })


def make_entity_claimed(entity_id: str, player_id: str) -> Message:
    """Create an ENTITY_CLAIMED broadcast.

    :param entity_id: The claimed entity's name/ID.
    :type entity_id: str
    :param player_id: The player who claimed it.
    :type player_id: str
    :return: An ENTITY_CLAIMED message.
    :rtype: Message
    """
    return Message(type=MessageType.ENTITY_CLAIMED, payload={
        "entity_id": entity_id,
        "player_id": player_id,
    })


def make_full_state(world_data: dict, entities: list, turn_data: dict) -> Message:
    """Create a FULL_STATE snapshot message.

    Sent to newly connected clients so they have the complete world state.

    :param world_data: Serialized world (tiles, entities, lore, turn).
    :type world_data: dict
    :param entities: List of serialized entity dicts.
    :type entities: list[dict]
    :param turn_data: Current turn/round information.
    :type turn_data: dict
    :return: A FULL_STATE message.
    :rtype: Message
    """
    return Message(type=MessageType.FULL_STATE, payload={
        "world": world_data,
        "entities": entities,
        "turn": turn_data,
    })


def make_state_delta(changes: list) -> Message:
    """Create a STATE_DELTA incremental update message.

    :param changes: List of change dicts from :func:`network.sync.compute_delta`.
    :type changes: list[dict]
    :return: A STATE_DELTA message.
    :rtype: Message
    """
    return Message(type=MessageType.STATE_DELTA, payload={
        "changes": changes,
    })


def make_action_request(action_type: str, params: dict) -> Message:
    """Create an ACTION_REQUEST from a player.

    :param action_type: The type of action (e.g. ``"move"``, ``"attack"``).
    :type action_type: str
    :param params: Action-specific parameters.
    :type params: dict
    :return: An ACTION_REQUEST message.
    :rtype: Message
    """
    return Message(type=MessageType.ACTION_REQUEST, payload={
        "action_type": action_type,
        "params": params,
    })


def make_action_result(success: bool, result: dict, state_delta: list) -> Message:
    """Create an ACTION_RESULT response from the host.

    :param success: Whether the action succeeded.
    :type success: bool
    :param result: Action outcome details.
    :type result: dict
    :param state_delta: State changes caused by the action.
    :type state_delta: list[dict]
    :return: An ACTION_RESULT message.
    :rtype: Message
    """
    return Message(type=MessageType.ACTION_RESULT, payload={
        "success": success,
        "result": result,
        "state_delta": state_delta,
    })


def make_turn_change(current_entity: str, round_number: int) -> Message:
    """Create a TURN_CHANGE broadcast.

    :param current_entity: Name of the entity whose turn it is.
    :type current_entity: str
    :param round_number: Current round number.
    :type round_number: int
    :return: A TURN_CHANGE message.
    :rtype: Message
    """
    return Message(type=MessageType.TURN_CHANGE, payload={
        "current_entity": current_entity,
        "round": round_number,
    })


def make_disconnect() -> Message:
    """Create a DISCONNECT message.

    :return: A DISCONNECT message with an empty payload.
    :rtype: Message
    """
    return Message(type=MessageType.DISCONNECT)


# --- Real-time collaboration ---


def make_cursor_update(
    player_id: str,
    player_name: str,
    x: float,
    y: float,
    color: str,
) -> Message:
    """Create a CURSOR_UPDATE message for real-time cursor sharing.

    :param player_id: Unique ID of the player whose cursor moved.
    :param player_name: Display name shown next to the cursor ghost.
    :param x: Scene X coordinate (float, not tile-snapped).
    :param y: Scene Y coordinate.
    :param color: Hex color string assigned to this player.
    :return: A CURSOR_UPDATE message.
    """
    return Message(type=MessageType.CURSOR_UPDATE, payload={
        "player_id": player_id,
        "player_name": player_name,
        "x": x,
        "y": y,
        "color": color,
    })


def make_ack(ack_seq: int) -> Message:
    """Create an ACK message acknowledging receipt of a critical message.

    :param ack_seq: The sequence number of the message being acknowledged.
    :return: An ACK message.
    """
    return Message(type=MessageType.ACK, payload={"ack_seq": ack_seq})


def make_draw_stroke(
    player_id: str,
    points: list,
    color: str,
) -> Message:
    """Create a DRAW_STROKE message for temporary line drawing.

    Sent as a complete polyline on mouse release. During drawing, only
    the local player sees their stroke.

    :param player_id: Unique ID of the player who drew the stroke.
    :param points: List of ``[x, y]`` coordinate pairs (scene coords).
    :param color: Hex color string for the stroke.
    :return: A DRAW_STROKE message.
    """
    return Message(type=MessageType.DRAW_STROKE, payload={
        "player_id": player_id,
        "points": points,
        "color": color,
    })


# --- Reliability classification ---

CRITICAL_TYPES: frozenset[MessageType] = frozenset({
    MessageType.WELCOME,
    MessageType.FULL_STATE,
    MessageType.ENTITY_CLAIMED,
    MessageType.ACTION_RESULT,
    MessageType.DRAW_STROKE,
    MessageType.TURN_CHANGE,
})

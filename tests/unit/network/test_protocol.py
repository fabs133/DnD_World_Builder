import pytest
from network.protocol import (
    Message, MessageType, ErrorCode, PROTOCOL_VERSION,
    make_hello, make_welcome, make_error, make_chat,
    make_claim_entity, make_entity_claimed,
    make_full_state, make_state_delta,
    make_action_request, make_action_result,
    make_turn_change, make_disconnect,
)


class TestMessageSerialization:

    def test_roundtrip_hello(self):
        msg = make_hello("Alice")
        restored = Message.from_json(msg.to_json())
        assert restored.type == MessageType.HELLO
        assert restored.payload["player_name"] == "Alice"
        assert restored.payload["version"] == PROTOCOL_VERSION

    def test_roundtrip_welcome(self):
        msg = make_welcome("sess1", "p1", [{"name": "Goblin"}])
        restored = Message.from_json(msg.to_json())
        assert restored.type == MessageType.WELCOME
        assert restored.payload["session_id"] == "sess1"
        assert restored.payload["player_id"] == "p1"
        assert restored.payload["entities"] == [{"name": "Goblin"}]

    def test_roundtrip_error(self):
        msg = make_error(ErrorCode.NOT_YOUR_TURN, "Wait your turn")
        restored = Message.from_json(msg.to_json())
        assert restored.type == MessageType.ERROR
        assert restored.payload["code"] == "NOT_YOUR_TURN"
        assert restored.payload["message"] == "Wait your turn"

    def test_roundtrip_chat(self):
        msg = make_chat("Alice", "Hello!")
        restored = Message.from_json(msg.to_json())
        assert restored.type == MessageType.CHAT
        assert restored.payload["sender"] == "Alice"
        assert restored.payload["message"] == "Hello!"

    def test_roundtrip_claim_entity(self):
        msg = make_claim_entity("Hero")
        restored = Message.from_json(msg.to_json())
        assert restored.type == MessageType.CLAIM_ENTITY
        assert restored.payload["entity_id"] == "Hero"

    def test_roundtrip_entity_claimed(self):
        msg = make_entity_claimed("Hero", "p1")
        restored = Message.from_json(msg.to_json())
        assert restored.type == MessageType.ENTITY_CLAIMED
        assert restored.payload["entity_id"] == "Hero"
        assert restored.payload["player_id"] == "p1"

    def test_roundtrip_full_state(self):
        world = {"tiles": {}, "entities": {}}
        entities = [{"name": "Hero"}]
        turn = {"current_turn": 0, "round": 1}
        msg = make_full_state(world, entities, turn)
        restored = Message.from_json(msg.to_json())
        assert restored.type == MessageType.FULL_STATE
        assert restored.payload["world"] == world
        assert restored.payload["entities"] == entities
        assert restored.payload["turn"] == turn

    def test_roundtrip_state_delta(self):
        changes = [{"op": "update", "path": "tiles/0,0", "value": {"terrain": "WATER"}}]
        msg = make_state_delta(changes)
        restored = Message.from_json(msg.to_json())
        assert restored.type == MessageType.STATE_DELTA
        assert restored.payload["changes"] == changes

    def test_roundtrip_action_request(self):
        msg = make_action_request("move", {"x": 1, "y": 2})
        restored = Message.from_json(msg.to_json())
        assert restored.type == MessageType.ACTION_REQUEST
        assert restored.payload["action_type"] == "move"
        assert restored.payload["params"] == {"x": 1, "y": 2}

    def test_roundtrip_action_result(self):
        msg = make_action_result(True, {"moved": True}, [])
        restored = Message.from_json(msg.to_json())
        assert restored.type == MessageType.ACTION_RESULT
        assert restored.payload["success"] is True
        assert restored.payload["result"] == {"moved": True}
        assert restored.payload["state_delta"] == []

    def test_roundtrip_turn_change(self):
        msg = make_turn_change("Goblin", 3)
        restored = Message.from_json(msg.to_json())
        assert restored.type == MessageType.TURN_CHANGE
        assert restored.payload["current_entity"] == "Goblin"
        assert restored.payload["round"] == 3

    def test_roundtrip_disconnect(self):
        msg = make_disconnect()
        restored = Message.from_json(msg.to_json())
        assert restored.type == MessageType.DISCONNECT
        assert restored.payload == {}

    def test_roundtrip_all_types(self):
        messages = [
            make_hello("Bob"),
            make_welcome("s", "p", []),
            make_error(ErrorCode.NOT_YOUR_TURN, "Wait"),
            make_chat("Alice", "Hello"),
            make_claim_entity("Goblin"),
            make_entity_claimed("Goblin", "p1"),
            make_full_state({}, [], {}),
            make_state_delta([{"op": "update", "path": "tiles/0,0", "value": {}}]),
            make_action_request("move", {"x": 1, "y": 2}),
            make_action_result(True, {"moved": True}, []),
            make_turn_change("Goblin", 3),
            make_disconnect(),
        ]
        for msg in messages:
            restored = Message.from_json(msg.to_json())
            assert restored.type == msg.type
            assert restored.payload == msg.payload


class TestMessageValidation:

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            Message.from_json("not json")

    def test_missing_type_raises(self):
        with pytest.raises(ValueError, match="missing 'type'"):
            Message.from_json('{"payload": {}}')

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown message type"):
            Message.from_json('{"type": "INVALID_TYPE"}')

    def test_missing_payload_defaults_to_empty(self):
        msg = Message.from_json('{"type": "DISCONNECT"}')
        assert msg.payload == {}

    def test_missing_seq_defaults_to_zero(self):
        msg = Message.from_json('{"type": "DISCONNECT"}')
        assert msg.seq == 0


class TestMessageTypeEnum:

    def test_all_types_defined(self):
        expected = {
            "HELLO", "WELCOME", "CLAIM_ENTITY", "ENTITY_CLAIMED",
            "FULL_STATE", "STATE_DELTA", "ACTION_REQUEST", "ACTION_RESULT",
            "TURN_CHANGE", "CHAT", "ERROR", "DISCONNECT",
            "CURSOR_UPDATE", "DRAW_STROKE",
            "PING", "PONG", "ACK",
            "VOICE_CAPABILITY", "VOICE_CHARACTER_ASSIGN",
            "VOICE_CHARACTER_PROGRESS", "VOICE_CHARACTER_COMPLETE",
            "VOICE_CACHE_SYNC",
        }
        actual = {t.value for t in MessageType}
        assert actual == expected


class TestSequenceNumber:

    def test_seq_preserved_in_roundtrip(self):
        msg = Message(type=MessageType.CHAT, seq=42, payload={"sender": "x", "message": "y"})
        restored = Message.from_json(msg.to_json())
        assert restored.seq == 42

    def test_timestamp_preserved_in_roundtrip(self):
        msg = make_hello("Alice")
        restored = Message.from_json(msg.to_json())
        assert restored.timestamp == msg.timestamp

    def test_timestamp_auto_set(self):
        msg = make_hello("Alice")
        assert msg.timestamp != ""
        assert "T" in msg.timestamp


class TestErrorCode:

    def test_all_error_codes_defined(self):
        expected = {
            "INVALID_MESSAGE", "NOT_YOUR_TURN", "ENTITY_ALREADY_CLAIMED",
            "UNKNOWN_ENTITY", "INVALID_ACTION", "VERSION_MISMATCH",
            "WRONG_PASSWORD",
        }
        actual = {c.value for c in ErrorCode}
        assert actual == expected

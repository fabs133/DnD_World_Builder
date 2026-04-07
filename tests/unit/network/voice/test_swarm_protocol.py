"""Tests for voice swarm protocol messages."""

import json
import pytest
from pathlib import Path

from network.protocol import MessageType, Message
from network.voice.swarm_protocol import (
    make_voice_capability,
    make_voice_character_assign,
    make_voice_character_progress,
    make_voice_character_complete,
    make_voice_cache_sync,
)


class TestVoiceCapability:
    def test_roundtrip(self):
        msg = make_voice_capability("gpu", vram_mb=8192, chatterbox_version="0.1.6")
        assert msg.type == MessageType.VOICE_CAPABILITY
        data = json.loads(msg.to_json())
        restored = Message.from_json(json.dumps(data))
        assert restored.payload["hardware_tier"] == "gpu"
        assert restored.payload["vram_mb"] == 8192


class TestVoiceCharacterAssign:
    def test_roundtrip(self):
        msg = make_voice_character_assign(
            character_id="marta_barkeep",
            entity_name="Marta",
            voice_seed_path=None,
            params={"exaggeration": 0.5, "speed_factor": 1.0},
            lines=[{"cache_key": "abc", "text": "Hello", "category": "greeting"}],
        )
        assert msg.type == MessageType.VOICE_CHARACTER_ASSIGN
        data = json.loads(msg.to_json())
        restored = Message.from_json(json.dumps(data))
        assert restored.payload["character_id"] == "marta_barkeep"
        assert len(restored.payload["lines"]) == 1

    def test_reads_seed_file(self, tmp_path):
        seed_file = tmp_path / "test_seed.wav"
        seed_file.write_bytes(b"RIFF" + b"\x00" * 100)

        msg = make_voice_character_assign(
            character_id="test",
            entity_name="Test",
            voice_seed_path=seed_file,
            params={},
            lines=[],
        )
        assert len(msg.payload["voice_seed_base64"]) > 0

    def test_missing_seed_file(self):
        msg = make_voice_character_assign(
            character_id="test",
            entity_name="Test",
            voice_seed_path="/nonexistent/path.wav",
            params={},
            lines=[],
        )
        assert msg.payload["voice_seed_base64"] == ""


class TestVoiceCharacterProgress:
    def test_roundtrip(self):
        msg = make_voice_character_progress("marta", completed=5, total=8)
        assert msg.type == MessageType.VOICE_CHARACTER_PROGRESS
        data = json.loads(msg.to_json())
        restored = Message.from_json(json.dumps(data))
        assert restored.payload["completed"] == 5
        assert restored.payload["total"] == 8


class TestVoiceCharacterComplete:
    def test_roundtrip(self):
        results = [
            {"cache_key": "abc", "text": "Hello", "audio_base64": "AAAA", "size_bytes": 100},
            {"cache_key": "def", "text": "Bye", "audio_base64": "BBBB", "size_bytes": 80},
        ]
        msg = make_voice_character_complete(
            "marta", "Marta", results, total_generation_time_ms=2400,
        )
        assert msg.type == MessageType.VOICE_CHARACTER_COMPLETE
        assert msg.payload["total_size_bytes"] == 180
        data = json.loads(msg.to_json())
        restored = Message.from_json(json.dumps(data))
        assert len(restored.payload["results"]) == 2


class TestVoiceCacheSync:
    def test_roundtrip(self):
        results = [{"cache_key": "abc", "text": "Hello", "audio_base64": "AAAA", "size_bytes": 100}]
        msg = make_voice_cache_sync("marta", "Marta", results)
        assert msg.type == MessageType.VOICE_CACHE_SYNC
        data = json.loads(msg.to_json())
        restored = Message.from_json(json.dumps(data))
        assert restored.payload["entity_name"] == "Marta"


class TestMessageTypesInEnum:
    def test_all_voice_types_exist(self):
        assert hasattr(MessageType, "VOICE_CAPABILITY")
        assert hasattr(MessageType, "VOICE_CHARACTER_ASSIGN")
        assert hasattr(MessageType, "VOICE_CHARACTER_PROGRESS")
        assert hasattr(MessageType, "VOICE_CHARACTER_COMPLETE")
        assert hasattr(MessageType, "VOICE_CACHE_SYNC")

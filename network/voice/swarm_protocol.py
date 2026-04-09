"""Voice swarm protocol message factory functions.

Character-level assignment: each worker receives one command per
character containing the voice seed, parameters, and full text list.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, List

from network.protocol import Message, MessageType


def make_voice_capability(
    hardware_tier: str,
    vram_mb: int = 0,
    chatterbox_version: str = "",
) -> Message:
    """Client reports its voice generation capability."""
    return Message(
        type=MessageType.VOICE_CAPABILITY,
        payload={
            "hardware_tier": hardware_tier,
            "vram_mb": vram_mb,
            "chatterbox_version": chatterbox_version,
        },
    )


def make_voice_character_assign(
    character_id: str,
    entity_name: str,
    voice_seed_path: str | Path | None,
    params: dict,
    lines: list[dict],
) -> Message:
    """DM assigns a character's voice generation to a worker.

    The voice seed is inlined as base64 in the message payload.
    """
    seed_b64 = ""
    if voice_seed_path:
        path = Path(voice_seed_path)
        if path.exists():
            seed_b64 = base64.b64encode(path.read_bytes()).decode("ascii")

    return Message(
        type=MessageType.VOICE_CHARACTER_ASSIGN,
        payload={
            "character_id": character_id,
            "entity_name": entity_name,
            "voice_seed_base64": seed_b64,
            "params": params,
            "lines": lines,
        },
    )


def make_voice_character_progress(
    character_id: str,
    completed: int,
    total: int,
) -> Message:
    """Worker reports generation progress for a character."""
    return Message(
        type=MessageType.VOICE_CHARACTER_PROGRESS,
        payload={
            "character_id": character_id,
            "completed": completed,
            "total": total,
        },
    )


def make_voice_character_complete(
    character_id: str,
    entity_name: str,
    results: list[dict],
    total_generation_time_ms: int = 0,
) -> Message:
    """Worker finished all lines for a character — batch result."""
    total_size = sum(r.get("size_bytes", 0) for r in results)
    return Message(
        type=MessageType.VOICE_CHARACTER_COMPLETE,
        payload={
            "character_id": character_id,
            "entity_name": entity_name,
            "results": results,
            "total_size_bytes": total_size,
            "total_generation_time_ms": total_generation_time_ms,
        },
    )


def make_voice_cache_sync(
    character_id: str,
    entity_name: str,
    results: list[dict],
) -> Message:
    """DM distributes completed character audio to all clients."""
    return Message(
        type=MessageType.VOICE_CACHE_SYNC,
        payload={
            "character_id": character_id,
            "entity_name": entity_name,
            "results": results,
        },
    )


# ── Player voice lines ──────────────────────────────────────────


def make_voice_line_share(
    player_name: str,
    lines: list[dict],
) -> Message:
    """Player sends their generated voice lines to the host.

    Each entry in *lines*: ``{text, category, cache_key, audio_base64, size_bytes}``.
    """
    return Message(
        type=MessageType.VOICE_LINE_SHARE,
        payload={
            "player_name": player_name,
            "lines": lines,
        },
    )


def make_voice_line_play(
    player_name: str,
    cache_key: str,
    text: str,
) -> Message:
    """Trigger playback of a voice line across all connected clients."""
    return Message(
        type=MessageType.VOICE_LINE_PLAY,
        payload={
            "player_name": player_name,
            "cache_key": cache_key,
            "text": text,
        },
    )

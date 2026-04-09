"""Player voice line data model and preset categories."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlayerVoiceLine:
    """A single voice line authored by a player."""

    text: str
    category: str = "custom"
    cache_key: str = ""


@dataclass
class PlayerVoiceLineSet:
    """All voice lines for one player, with generation/share state."""

    player_name: str
    lines: list[PlayerVoiceLine] = field(default_factory=list)
    reference_audio_path: Optional[str] = None
    generated: bool = False
    shared: bool = False

    def to_share_payload(self) -> list[dict]:
        """Convert lines to dicts for network transmission (without audio)."""
        return [
            {"text": l.text, "category": l.category, "cache_key": l.cache_key}
            for l in self.lines
        ]

    @staticmethod
    def from_share_payload(player_name: str, data: list[dict]) -> PlayerVoiceLineSet:
        """Reconstruct from received network payload."""
        lines = [
            PlayerVoiceLine(
                text=d["text"],
                category=d.get("category", "custom"),
                cache_key=d.get("cache_key", ""),
            )
            for d in data
        ]
        return PlayerVoiceLineSet(player_name=player_name, lines=lines)


# ── Preset voice line suggestions ────────────────────────────────

VOICE_LINE_CATEGORIES = [
    "greeting",
    "combat_attack",
    "combat_defend",
    "exploration",
    "social",
    "reaction",
    "custom",
]

PLAYER_VOICE_LINE_PRESETS: dict[str, list[str]] = {
    "greeting": ["Hail, friends!", "Well met!"],
    "combat_attack": ["Attack!", "For glory!", "Have at thee!"],
    "combat_defend": ["Fall back!", "Shield up!", "Heal me!"],
    "exploration": ["I search the room.", "I check for traps.", "I move ahead."],
    "social": ["I agree.", "I disagree.", "Let me think..."],
    "reaction": ["By the gods!", "Excellent!", "That's not good."],
    "custom": [],
}

MAX_VOICE_LINES = 20


def default_voice_lines() -> list[PlayerVoiceLine]:
    """Return a starter set of voice lines from presets (one per category)."""
    lines = []
    for category, texts in PLAYER_VOICE_LINE_PRESETS.items():
        if texts:
            lines.append(PlayerVoiceLine(text=texts[0], category=category))
    return lines

"""Session state capture and restoration for mid-session save/load."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class SessionState:
    """Complete snapshot of a play session, serializable to JSON.

    Captures everything needed to resume: entities, play state,
    initiative, side events, and quest progress.
    """

    play_state: str = "EXPLORATION"           # EXPLORATION | COMBAT
    timestamp: float = 0.0

    # Entity state (full to_dict for each)
    entities: list[dict] = field(default_factory=list)
    tile_dicts: list[dict] = field(default_factory=list)

    # Combat state (only if play_state == COMBAT)
    initiative_order: list[str] = field(default_factory=list)
    current_turn_index: int = 0
    round_number: int = 1

    # Exploration state
    current_tile_pos: Optional[tuple[int, int]] = None
    side_event_state: dict = field(default_factory=dict)  # str(pos) → status

    # Quest state
    quest_state: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "play_state": self.play_state,
            "timestamp": self.timestamp,
            "entities": self.entities,
            "tile_dicts": self.tile_dicts,
            "initiative_order": self.initiative_order,
            "current_turn_index": self.current_turn_index,
            "round_number": self.round_number,
            "current_tile_pos": list(self.current_tile_pos) if self.current_tile_pos else None,
            "side_event_state": self.side_event_state,
            "quest_state": self.quest_state,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SessionState:
        pos = data.get("current_tile_pos")
        return cls(
            play_state=data.get("play_state", "EXPLORATION"),
            timestamp=data.get("timestamp", 0),
            entities=data.get("entities", []),
            tile_dicts=data.get("tile_dicts", []),
            initiative_order=data.get("initiative_order", []),
            current_turn_index=data.get("current_turn_index", 0),
            round_number=data.get("round_number", 1),
            current_tile_pos=tuple(pos) if pos else None,
            side_event_state=data.get("side_event_state", {}),
            quest_state=data.get("quest_state", []),
        )

    def save(self, path: Path) -> None:
        """Write session state to a JSON file."""
        self.timestamp = time.time()
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
                        encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> SessionState:
        """Load session state from a JSON file."""
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)


def capture_session(play_state_str: str,
                    all_entities: list,
                    tile_dicts: list[dict],
                    current_tile_pos=None,
                    side_event_state: dict | None = None,
                    quest_tracker=None) -> SessionState:
    """Capture the current session state from live objects."""
    entities = []
    for e in all_entities:
        if hasattr(e, "to_dict"):
            entities.append(e.to_dict())

    # Convert side_event_state keys from tuples to strings for JSON
    se_state = {}
    if side_event_state:
        for pos, state in side_event_state.items():
            key = f"{pos[0]},{pos[1]}" if isinstance(pos, tuple) else str(pos)
            se_state[key] = state

    quest_state = []
    if quest_tracker and hasattr(quest_tracker, "to_dict"):
        quest_state = quest_tracker.to_dict()

    return SessionState(
        play_state=play_state_str,
        entities=entities,
        tile_dicts=tile_dicts,
        current_tile_pos=current_tile_pos,
        side_event_state=se_state,
        quest_state=quest_state,
    )

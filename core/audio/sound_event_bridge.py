"""Auto-trigger sounds from EventBus game events.

Central wiring between game logic events and audio feedback.
Handles multiplayer local-player filtering.
"""

from __future__ import annotations

import logging
from typing import Any

from core.audio.ui_sound_manager import UISoundManager, SoundCategory
from core.events import (
    COMBAT_ENDED, COMBAT_STARTED, ENTITY_DAMAGED, ENTITY_DIED,
    INITIATIVE_ROLLED, ROUND_STARTED, TURN_STARTED,
)

logger = logging.getLogger(__name__)


class SoundEventBridge:
    """Subscribes to EventBus events and plays appropriate sounds.

    :param sound_manager: UISoundManager instance.
    :param viewer_entity_name: Local player's entity name (empty for DM).
    """

    _instance: "SoundEventBridge | None" = None

    @classmethod
    def instance(cls) -> "SoundEventBridge | None":
        """Return the global bridge instance (set in entry_point.py)."""
        return cls._instance

    def __init__(
        self,
        sound_manager: UISoundManager,
        viewer_entity_name: str = "",
    ):
        self._sound = sound_manager
        self._viewer = viewer_entity_name
        self._subscribed = False
        self._handlers: list[tuple[str, Any]] = []

    def set_viewer(self, entity_name: str) -> None:
        """Update local player identity."""
        self._viewer = entity_name

    def start(self) -> None:
        """Subscribe to all game events."""
        if self._subscribed:
            return
        from core.gameCreation.event_bus import EventBus

        mappings = [
            # Always play
            (COMBAT_STARTED, self._on_combat_started),
            (COMBAT_ENDED, self._on_combat_ended),
            (INITIATIVE_ROLLED, self._on_initiative),
            (ROUND_STARTED, self._on_round_started),
            (ENTITY_DIED, self._on_entity_died),
            # Local-aware
            (TURN_STARTED, self._on_turn_started),
            (ENTITY_DAMAGED, self._on_entity_damaged),
        ]

        for event_type, handler in mappings:
            EventBus.subscribe(event_type, handler)
            self._handlers.append((event_type, handler))

        self._subscribed = True

    def stop(self) -> None:
        """Unsubscribe from all events."""
        if not self._subscribed:
            return
        from core.gameCreation.event_bus import EventBus

        for event_type, handler in self._handlers:
            EventBus.unsubscribe(event_type, handler)
        self._handlers.clear()
        self._subscribed = False

    def _is_local(self, entity_name: str) -> bool:
        """Check if the entity is the local player (or DM sees all)."""
        if not self._viewer:
            return True  # DM hears everything
        return entity_name == self._viewer

    # ── Event handlers ───────────────────────────────────────────────

    def _on_combat_started(self, data: dict) -> None:
        self._sound.play_shared("combat_start", SoundCategory.ALERT)

    def _on_combat_ended(self, data: dict) -> None:
        outcome = data.get("outcome", "victory")
        if outcome == "defeat":
            self._sound.play_shared("defeat", SoundCategory.ALERT)
        else:
            self._sound.play_shared("victory", SoundCategory.ALERT)

    def _on_initiative(self, data: dict) -> None:
        self._sound.play_shared("initiative", SoundCategory.COMBAT)

    def _on_round_started(self, data: dict) -> None:
        self._sound.play_shared("round_bell", SoundCategory.COMBAT)

    def _on_turn_started(self, data: dict) -> None:
        entity_name = data.get("entity", "")
        if isinstance(entity_name, str):
            name = entity_name
        else:
            name = getattr(entity_name, "name", "")
        if self._is_local(name):
            self._sound.play_shared("your_turn", SoundCategory.ALERT)

    def _on_entity_damaged(self, data: dict) -> None:
        target = data.get("target", "")
        if isinstance(target, str):
            target_name = target
        else:
            target_name = getattr(target, "name", "")

        # Try to play a weapon-specific sound based on damage_type
        damage_type = data.get("damage_type", "weapon")
        if damage_type in ("fire", "ice", "lightning", "thunder"):
            self._sound.play(f"attacks/spells/{damage_type}", SoundCategory.COMBAT)
            return
        elif damage_type == "ranged":
            self._sound.play("attacks/bow/bow_impact_hit", SoundCategory.COMBAT)
            return

        # Fallback to generic damage sounds
        if self._is_local(target_name):
            self._sound.play("damage_taken", SoundCategory.ALERT)
        else:
            # Try sword hit first, fall back to generic
            if self._sound.resolve_path("attacks/sword/sword_impact_hit"):
                self._sound.play("attacks/sword/sword_impact_hit", SoundCategory.COMBAT)
            else:
                self._sound.play("damage_dealt", SoundCategory.COMBAT)

    def _on_entity_died(self, data: dict) -> None:
        # Try monster death sound, fall back to generic
        if self._sound.resolve_path("monsters/basic/creature_die"):
            self._sound.play("monsters/basic/creature_die", SoundCategory.COMBAT)
        else:
            self._sound.play("enemy_down", SoundCategory.COMBAT)

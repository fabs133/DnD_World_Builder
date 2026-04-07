"""Combat animation orchestrator — subscribes to events, spawns effects."""

from __future__ import annotations
from typing import Callable, Optional

from PyQt5.QtCore import QPointF, QTimer
from PyQt5.QtWidgets import QGraphicsScene

from core.events import (
    ATTACK_MISSED, COMBAT_ENDED, CONDITION_APPLIED, CONDITION_REMOVED,
    ENTITY_DAMAGED, ENTITY_DIED, ENTITY_HEALED, ROUND_STARTED,
    SPELL_CAST, TURN_STARTED,
)
from core.gameCreation.event_bus import EventBus
from ui.animations.floating_text import FloatingText
from ui.animations.token_animator import TokenAnimator
from ui.animations.particle_item import ParticleItem
from ui.animations.presets import get_preset, CONDITION_PRESETS


class CombatAnimator:
    """Subscribes to combat events, renders animations + particles.

    Purely presentational — never mutates game state.
    """

    SUBSCRIBE_EVENTS = [
        ENTITY_DIED, TURN_STARTED, ROUND_STARTED, COMBAT_ENDED,
        ENTITY_DAMAGED, ENTITY_HEALED, ATTACK_MISSED,
        SPELL_CAST, CONDITION_APPLIED, CONDITION_REMOVED,
    ]

    def __init__(self, scene: QGraphicsScene | None = None,
                 tile_lookup: Callable | None = None):
        """
        Args:
            scene: The QGraphicsScene to add effects to.
            tile_lookup: callable(row, col) -> CombatTileItem | None
        """
        self._scene = scene
        self._tile_lookup = tile_lookup or (lambda r, c: None)
        self._enabled = True
        self._game_particles: dict[str, ParticleItem] = {}
        self._status_particles: dict[tuple[str, str], ParticleItem] = {}

        for event in self.SUBSCRIBE_EVENTS:
            EventBus.subscribe(event, getattr(self, f"_on_{event}"))

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def set_scene(self, scene: QGraphicsScene, tile_lookup=None) -> None:
        self._scene = scene
        if tile_lookup:
            self._tile_lookup = tile_lookup

    def cleanup(self) -> None:
        for event in self.SUBSCRIBE_EVENTS:
            try:
                EventBus.unsubscribe(event, getattr(self, f"_on_{event}"))
            except Exception:
                pass
        for pi in self._game_particles.values():
            pi.stop()
        self._game_particles.clear()
        for pi in self._status_particles.values():
            pi.stop()
        self._status_particles.clear()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _tile_center(self, pos: tuple) -> QPointF | None:
        """Resolve (row, col) to pixel center via tile_lookup."""
        tile = self._tile_lookup(pos[0], pos[1])
        if not tile:
            return None
        tile_pos = tile.pos()
        ts = getattr(tile, '_tile_size', 36)
        return QPointF(tile_pos.x() + ts / 2, tile_pos.y() + ts / 2)

    def _resolve_position(self, data: dict) -> tuple | None:
        """Extract (row, col) from event data, trying common key names."""
        pos = data.get("position")
        if pos and len(pos) >= 2:
            return (pos[0], pos[1])
        row = data.get("row")
        col = data.get("col")
        if row is not None and col is not None:
            return (row, col)
        return None

    # ------------------------------------------------------------------
    # Direct-call methods (called by PlaySessionDialog after ActionResult)
    # ------------------------------------------------------------------

    # Duration of the longest animation in a damage/miss/heal sequence.
    # FloatingText = 800ms, shake = 200ms, lunge = 250ms (all run in parallel).
    _ANIM_DURATION_MS = 850  # 800ms + 50ms buffer

    def on_damage(self, target_name: str, target_pos: tuple,
                  damage: int, is_crit: bool = False,
                  source_pos: tuple | None = None,
                  done_callback=None) -> None:
        if not self._enabled or not self._scene:
            if done_callback:
                QTimer.singleShot(0, done_callback)
            return

        row, col = target_pos
        tile = self._tile_lookup(row, col)
        if not tile:
            if done_callback:
                QTimer.singleShot(0, done_callback)
            return

        tile_pos = tile.pos()
        ts = getattr(tile, '_tile_size', 36)
        center = QPointF(tile_pos.x() + ts / 2, tile_pos.y() + ts / 2)

        # Floating damage number
        text = f"CRIT! -{damage}" if is_crit else f"-{damage}"
        color = "#e8b84b" if is_crit else "#c0392b"
        font_size = 18 if is_crit else 14
        ft = FloatingText(text, QPointF(center.x() - 10, center.y() - 20),
                          color=color, font_size=font_size)
        self._scene.addItem(ft)
        ft.play()

        # Impact particles
        preset_name = "crit_burst" if is_crit else "slash_sparks"
        self._spawn_preset(preset_name, center)

        # Shake defender tile
        TokenAnimator.shake(tile, duration_ms=200)

        # Lunge attacker
        if source_pos:
            src_tile = self._tile_lookup(source_pos[0], source_pos[1])
            if src_tile and src_tile is not tile:
                TokenAnimator.lunge(src_tile, tile_pos, duration_ms=250)

        if done_callback:
            QTimer.singleShot(self._ANIM_DURATION_MS, done_callback)

    def on_miss(self, target_name: str, target_pos: tuple,
                done_callback=None) -> None:
        if not self._enabled or not self._scene:
            if done_callback:
                QTimer.singleShot(0, done_callback)
            return
        row, col = target_pos
        tile = self._tile_lookup(row, col)
        if not tile:
            if done_callback:
                QTimer.singleShot(0, done_callback)
            return
        tile_pos = tile.pos()
        ts = getattr(tile, '_tile_size', 36)
        ft = FloatingText("MISS", QPointF(tile_pos.x() + ts / 2 - 10, tile_pos.y() - 5),
                          color="#6b5d47", font_size=12)
        self._scene.addItem(ft)
        ft.play()

        if done_callback:
            QTimer.singleShot(self._ANIM_DURATION_MS, done_callback)

    def on_heal(self, target_name: str, target_pos: tuple, amount: int,
                done_callback=None) -> None:
        if not self._enabled or not self._scene:
            if done_callback:
                QTimer.singleShot(0, done_callback)
            return
        row, col = target_pos
        tile = self._tile_lookup(row, col)
        if not tile:
            if done_callback:
                QTimer.singleShot(0, done_callback)
            return
        tile_pos = tile.pos()
        ts = getattr(tile, '_tile_size', 36)
        center = QPointF(tile_pos.x() + ts / 2, tile_pos.y() + ts / 2)
        ft = FloatingText(f"+{amount}", QPointF(center.x() - 10, center.y() - 20),
                          color="#4caf50", font_size=14)
        self._scene.addItem(ft)
        ft.play()
        self._spawn_preset("healing_aura", center)

        if done_callback:
            QTimer.singleShot(self._ANIM_DURATION_MS, done_callback)

    # ------------------------------------------------------------------
    # EventBus handlers
    # ------------------------------------------------------------------

    def _on_entity_died(self, data: dict) -> None:
        if not self._enabled or not self._scene:
            return
        name = data.get("entity") or data.get("entity_name")
        pos = self._resolve_position(data)
        if not pos:
            return
        center = self._tile_center(pos)
        if not center:
            return
        ft = FloatingText("DEFEATED", QPointF(center.x() - 20, center.y() - 30),
                          color="#c0392b", font_size=16, duration_ms=1200)
        self._scene.addItem(ft)
        ft.play()

    def _on_entity_damaged(self, data: dict) -> None:
        """EventBus-driven damage handler — parses event dict."""
        if not self._enabled or not self._scene:
            return
        target_name = data.get("entity_name") or data.get("target") or ""
        damage = data.get("damage") or data.get("amount", 0)
        is_crit = data.get("critical", False)

        pos = self._resolve_position(data)
        if not pos:
            return

        source_pos = data.get("source_position")
        self.on_damage(target_name, pos, damage, is_crit, source_pos)

    def _on_entity_healed(self, data: dict) -> None:
        """EventBus-driven heal handler."""
        if not self._enabled or not self._scene:
            return
        target_name = data.get("entity_name") or data.get("target") or ""
        amount = data.get("amount", 0)
        pos = self._resolve_position(data)
        if not pos:
            return
        self.on_heal(target_name, pos, amount)

    def _on_attack_missed(self, data: dict) -> None:
        """EventBus-driven miss handler."""
        if not self._enabled or not self._scene:
            return
        target_name = data.get("target") or data.get("entity_name") or ""
        pos = self._resolve_position(data)
        if not pos:
            return
        self.on_miss(target_name, pos)

    def _on_spell_cast(self, data: dict) -> None:
        """Spawn spell_flash particles at target position."""
        if not self._enabled or not self._scene:
            return
        pos = self._resolve_position(data)
        if not pos:
            return
        center = self._tile_center(pos)
        if not center:
            return
        self._spawn_preset("spell_flash", center)

    def _on_condition_applied(self, data: dict) -> None:
        """STATUS particles — start when a condition is applied to an entity."""
        if not self._enabled or not self._scene:
            return
        entity_name = data.get("entity_name") or data.get("entity") or ""
        condition = data.get("condition") or data.get("name") or ""
        if not entity_name or not condition:
            return

        preset_name = CONDITION_PRESETS.get(condition)
        if not preset_name:
            return

        key = (entity_name, condition)
        if key in self._status_particles:
            return  # Already showing this condition

        pos = self._resolve_position(data)
        if not pos:
            return
        center = self._tile_center(pos)
        if not center:
            return

        item = self._spawn_preset(preset_name, center)
        if item:
            self._status_particles[key] = item

    def _on_condition_removed(self, data: dict) -> None:
        """STATUS particles — stop when a condition is removed."""
        entity_name = data.get("entity_name") or data.get("entity") or ""
        condition = data.get("condition") or data.get("name") or ""
        key = (entity_name, condition)
        item = self._status_particles.pop(key, None)
        if item:
            item.stop()

    def _on_turn_started(self, data: dict) -> None:
        if not self._enabled or not self._scene:
            return
        # Stop previous active turn indicator
        old = self._game_particles.pop("active_turn", None)
        if old:
            old.stop()

        pos = self._resolve_position(data)
        if not pos:
            return
        center = self._tile_center(pos)
        if not center:
            return
        item = self._spawn_preset("active_turn", center)
        if item:
            self._game_particles["active_turn"] = item

    def _on_round_started(self, data: dict) -> None:
        pass  # Could add round_start flash

    def _on_combat_ended(self, data: dict) -> None:
        # Stop all managed particles
        for pi in self._game_particles.values():
            pi.stop()
        self._game_particles.clear()
        for pi in self._status_particles.values():
            pi.stop()
        self._status_particles.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _spawn_preset(self, preset_name: str, pos: QPointF) -> ParticleItem | None:
        if not self._scene:
            return None
        preset = get_preset(preset_name)
        if not preset:
            return None
        item = ParticleItem(preset, pos)
        self._scene.addItem(item)
        item.start()
        return item

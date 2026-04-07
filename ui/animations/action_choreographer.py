"""Action choreographer — multi-phase animation sequencer for combat actions.

Reads an :class:`ActionResult` from the game engine and decomposes it into
a timed :class:`ChoreographySequence` (intent → approach → impact → aftermath).
Each phase triggers visual effects via existing subsystems, then chains into
the next phase via ``QTimer.singleShot``.

The game engine is never modified — this is pure presentation.
"""

from __future__ import annotations

import re
from typing import Callable, Any, TYPE_CHECKING

from PyQt5.QtCore import QTimer, QPointF

from core.logger import app_logger
from ui.animations.choreography_data import (
    ChoreographyEffect, ChoreographySequence, EffectType, PhaseStep,
    MELEE_HIT, MELEE_CRIT, MELEE_MISS, SPELL_HIT, HEAL, SIMPLE_ACTION,
)

if TYPE_CHECKING:
    from core.engine.action_executor import ActionResult
    from ui.animations.combat_animator import CombatAnimator
    from ui.combat.combat_tile_item import CombatTileItem
    from PyQt5.QtWidgets import QGraphicsScene


class ActionChoreographer:
    """Orchestrates multi-phase visual sequences for combat actions.

    Usage::

        choreographer = ActionChoreographer(scene, tile_lookup)
        started = choreographer.play(result, done_callback=callback)
    """

    def __init__(
        self,
        scene: "QGraphicsScene | None" = None,
        tile_lookup: Callable | None = None,
        animator: "CombatAnimator | None" = None,
    ):
        self._scene = scene
        self._tile_lookup = tile_lookup or (lambda r, c: None)
        self._animator = animator
        self._playing = False

    @property
    def is_playing(self) -> bool:
        return self._playing

    def play(
        self,
        result: "ActionResult",
        done_callback: Callable | None = None,
        camera_pan_fn: Callable | None = None,
        update_table_fn: Callable | None = None,
    ) -> bool:
        """Start choreographing an action result.

        :returns: True if choreography started, False if caller should fallback.
        """
        if not result or not result.action:
            return False

        if self._playing:
            return False  # Don't overlap

        ctx = self._extract_context(result)
        if ctx is None:
            return False

        seq = self._select_sequence(result, ctx)
        ctx["camera_pan_fn"] = camera_pan_fn
        ctx["update_table_fn"] = update_table_fn

        self._playing = True
        app_logger.debug(
            f"[Choreographer] {seq.name}: {len(seq.steps)} phases, "
            f"{seq.total_duration_ms}ms"
        )

        steps = list(seq.steps)
        self._walk_steps(steps, ctx, done_callback)
        return True

    def cancel(self) -> None:
        self._playing = False

    # ------------------------------------------------------------------
    # Context extraction
    # ------------------------------------------------------------------

    def _extract_context(self, result: "ActionResult") -> dict | None:
        """Parse ActionResult into a runtime context dict."""
        action = result.action
        actor = getattr(action, "actor", None)
        target = getattr(action, "target", None)
        if not actor:
            return None

        log_text = " ".join(result.execution_log).lower()

        # Extract damage
        damage = 0
        for line in result.execution_log:
            if "damage" in line.lower():
                nums = re.findall(r'\d+', line)
                if nums:
                    damage = int(nums[0])
                    break

        # Extract heal amount
        heal = 0
        for line in result.execution_log:
            if "heal" in line.lower():
                nums = re.findall(r'\d+', line)
                if nums:
                    heal = int(nums[0])
                    break

        return {
            "actor": actor,
            "target": target,
            "actor_name": getattr(actor, "name", "?"),
            "target_name": getattr(target, "name", "?") if target else "",
            "actor_pos": getattr(actor, "position", None),
            "target_pos": getattr(target, "position", None),
            "damage": str(damage),
            "heal": str(heal),
            "is_crit": "critical" in log_text or "crit" in log_text,
            "success": result.success,
        }

    # ------------------------------------------------------------------
    # Sequence selection
    # ------------------------------------------------------------------

    def _select_sequence(self, result: "ActionResult", ctx: dict) -> ChoreographySequence:
        action_type = result.action.__class__.__name__
        log_text = " ".join(result.execution_log).lower()

        if action_type == "AttackAction":
            if result.success and "miss" not in log_text:
                return MELEE_CRIT if ctx["is_crit"] else MELEE_HIT
            return MELEE_MISS

        if action_type == "SpellAction":
            if result.success and "heal" in log_text:
                return HEAL
            if result.success:
                return SPELL_HIT
            return MELEE_MISS

        return SIMPLE_ACTION

    # ------------------------------------------------------------------
    # Phase walking
    # ------------------------------------------------------------------

    def _walk_steps(
        self,
        steps: list[PhaseStep],
        ctx: dict,
        done_callback: Callable | None,
    ) -> None:
        if not self._playing or not steps:
            self._playing = False
            if done_callback:
                done_callback()
            return

        step = steps.pop(0)
        self._fire_effects(step, ctx)
        QTimer.singleShot(
            step.duration_ms,
            lambda: self._walk_steps(steps, ctx, done_callback),
        )

    def _fire_effects(self, step: PhaseStep, ctx: dict) -> None:
        for effect in step.effects:
            try:
                self._dispatch_effect(effect, ctx)
            except Exception:
                pass  # Animation failures should never crash the turn loop

    def _dispatch_effect(self, effect: ChoreographyEffect, ctx: dict) -> None:
        if effect.effect_type == EffectType.TOKEN_ANIM:
            self._fire_token_anim(effect, ctx)
        elif effect.effect_type == EffectType.PARTICLE:
            self._fire_particle(effect, ctx)
        elif effect.effect_type == EffectType.FLOATING_TEXT:
            self._fire_floating_text(effect, ctx)
        elif effect.effect_type == EffectType.SOUND:
            self._fire_sound(effect, ctx)
        elif effect.effect_type == EffectType.HIGHLIGHT:
            self._fire_highlight(effect, ctx)
        elif effect.effect_type == EffectType.UPDATE_HP:
            fn = ctx.get("update_table_fn")
            if fn:
                fn()

    # ------------------------------------------------------------------
    # Effect dispatch
    # ------------------------------------------------------------------

    # Map effect target names to context key prefixes
    _TARGET_TO_CTX = {"attacker": "actor", "defender": "target"}

    def _get_tile(self, target: str, ctx: dict):
        ctx_key = self._TARGET_TO_CTX.get(target, target)
        pos = ctx.get(f"{ctx_key}_pos")
        if pos and self._tile_lookup:
            return self._tile_lookup(pos[0], pos[1])
        return None

    def _fire_token_anim(self, effect: ChoreographyEffect, ctx: dict) -> None:
        tile = self._get_tile(effect.target, ctx)
        if not tile:
            return
        from ui.animations.token_animator import TokenAnimator
        anim = effect.params.get("anim", "").upper()
        if anim == "LUNGE":
            other = "defender" if effect.target == "attacker" else "attacker"
            dest_tile = self._get_tile(other, ctx)
            if dest_tile:
                TokenAnimator.lunge(tile, dest_tile.pos(), duration_ms=250)
        elif anim == "SHAKE":
            TokenAnimator.shake(tile, duration_ms=200)
        elif anim == "RECOIL":
            other = "defender" if effect.target == "attacker" else "attacker"
            dest_tile = self._get_tile(other, ctx)
            if dest_tile:
                TokenAnimator.recoil(tile, dest_tile.pos(), duration_ms=200)

    def _fire_particle(self, effect: ChoreographyEffect, ctx: dict) -> None:
        tile = self._get_tile(effect.target, ctx)
        if not tile or not self._animator:
            return
        tile_pos = tile.pos()
        ts = getattr(tile, '_tile_size', 36)
        center = QPointF(tile_pos.x() + ts / 2, tile_pos.y() + ts / 2)
        preset_name = effect.params.get("preset", "")
        if preset_name:
            self._animator._spawn_preset(preset_name, center)

    def _fire_floating_text(self, effect: ChoreographyEffect, ctx: dict) -> None:
        tile = self._get_tile(effect.target, ctx)
        if not tile or not self._scene:
            return
        tile_pos = tile.pos()
        ts = getattr(tile, '_tile_size', 36)

        template = effect.params.get("text", "")
        try:
            text = template.format(**ctx)
        except (KeyError, ValueError):
            text = template

        if not text or text == "-0":
            return

        color = effect.params.get("color", "#c0392b")
        size = int(effect.params.get("size", "14"))

        from ui.animations.floating_text import FloatingText
        ft = FloatingText(
            text,
            QPointF(tile_pos.x() + ts / 2 - 10, tile_pos.y() - 20),
            color=color,
            font_size=size,
        )
        self._scene.addItem(ft)
        ft.play()

    def _fire_sound(self, effect: ChoreographyEffect, ctx: dict) -> None:
        sound_id = effect.params.get("id", "")
        if not sound_id:
            return
        from core.audio.ui_sound_manager import UISoundManager, SoundCategory
        category = effect.params.get("category", "combat")
        cat = SoundCategory(category) if category else SoundCategory.COMBAT
        UISoundManager.instance().play(sound_id, cat)

    def _fire_highlight(self, effect: ChoreographyEffect, ctx: dict) -> None:
        tile = self._get_tile(effect.target, ctx)
        if tile and hasattr(tile, 'pulse_select'):
            from PyQt5.QtGui import QColor
            tile.pulse_select(QColor(220, 180, 40, 80), 200)

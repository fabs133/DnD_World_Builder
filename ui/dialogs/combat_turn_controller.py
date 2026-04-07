"""Combat turn controller — manages the turn loop, initiative, and session lifecycle.

Extracted from PlaySessionDialog to reduce its size.  Receives all
dependencies via the constructor; does NOT hold a back-reference to the dialog.
"""

from __future__ import annotations

import re
from typing import Optional, TYPE_CHECKING

from PyQt5.QtCore import QTimer

from core.audio.ui_sound_manager import UISoundManager, SoundCategory
from core.engine.play_state import PlayState

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QLabel, QTextEdit, QPushButton
    from core.engine.play_session import PlaySessionRunner
    from core.engine.info_filter import InfoFilter
    from ui.combat.action_bar_panel import ActionBarPanel
    from ui.panels.initiative_panel import InitiativePanel
    from ui.combat.play_map_widget import PlayMapScene


class CombatTurnController:
    """Drives the AI/player turn loop and tracks combat session state.

    The controller never touches widget *creation* or layout — only
    updates widgets that are handed to it.
    """

    def __init__(
        self,
        *,
        get_play_state,
        set_play_state,
        get_runner,
        get_ui_adapter,
        get_is_running,
        set_is_running,
        get_combat_scene,
        get_mini_map_scene,
        get_map_scene,
        get_animator,
        set_animator,
        get_info_filter,
        turn_label: "QLabel",
        log: "QTextEdit",
        action_bar: "ActionBarPanel",
        move_btn: "QPushButton",
        initiative_panel: "InitiativePanel",
        initiative_section,
        on_enter_exploration,
        on_advance_turns_ready,
        on_combat_finished=None,
        get_combat_map_view=None,
        run_transition=None,
        get_choreographer=None,
        encounter_strip=None,
    ):
        # Accessors (callables) — avoids stale references
        self._get_play_state = get_play_state
        self._set_play_state = set_play_state
        self._get_runner = get_runner
        self._get_ui_adapter = get_ui_adapter
        self._get_is_running = get_is_running
        self._set_is_running = set_is_running
        self._get_combat_scene = get_combat_scene
        self._get_mini_map_scene = get_mini_map_scene
        self._get_map_scene = get_map_scene
        self._get_animator = get_animator
        self._set_animator = set_animator
        self._get_info_filter = get_info_filter

        # Widgets (stable references)
        self._turn_label = turn_label
        self._log = log
        self._action_bar = action_bar
        self._move_btn = move_btn
        self._initiative_panel = initiative_panel
        self._initiative_section = initiative_section

        # Callbacks into the dialog
        self._on_enter_exploration = on_enter_exploration
        self._on_advance_turns_ready = on_advance_turns_ready
        self._on_combat_finished = on_combat_finished
        self._get_combat_map_view = get_combat_map_view
        self._run_transition = run_transition
        self._get_choreographer = get_choreographer
        self._encounter_strip = encounter_strip
        self._step_ready = True  # Gate: False = waiting for animations

    # ------------------------------------------------------------------
    # Turn loop
    # ------------------------------------------------------------------

    def release_step(self) -> None:
        """Called by the encounter strip when its animation is done.
        Unblocks the turn loop so the next turn can proceed."""
        self._step_ready = True
        QTimer.singleShot(50, self.advance_turns)

    def advance_turns(self) -> None:
        """Advance exactly ONE turn, then STOP until release_step() is called.

        The step gate ensures animations play fully before the next turn.
        Non-attack turns release immediately (no animation to wait for).
        """
        # Gate: if step not ready, do nothing — release_step will re-call us
        if not self._step_ready:
            return
        if self._get_play_state() != PlayState.COMBAT:
            return
        if not self._get_is_running() or not self._get_runner():
            return
        runner = self._get_runner()
        if runner.is_finished:
            self._notify_combat_finished()
            return

        is_player = runner.is_player_turn()
        name = runner.current_entity_name()
        self._center_camera_on_entity(name)

        if is_player:
            self._turn_label.setText(f"Your turn: {name}")
            self._turn_label.setStyleSheet(
                "font-size: 16px; font-weight: bold; padding: 6px; color: #22c55e;")
            # Sound handled by SoundEventBridge (TURN_STARTED)
        else:
            self._turn_label.setText(f"AI turn: {name or '?'}")
            self._turn_label.setStyleSheet(
                "font-size: 16px; font-weight: bold; padding: 6px; color: #888;")
            self._action_bar.hide()
            self._move_btn.hide()

        # Track round number
        session = getattr(runner, '_session', None)
        initiative = getattr(session, '_initiative', None)
        old_round = getattr(initiative, 'round_number', 0) if initiative else 0

        result = runner.run_one_turn()

        # Round change sound
        new_round = getattr(initiative, 'round_number', 0) if initiative else 0
        # Round change sound handled by SoundEventBridge (ROUND_STARTED)

        # If this was an attack, BLOCK until encounter strip calls release_step()
        is_attack = False
        try:
            action = getattr(result, "action", None)
            if action:
                is_attack = action.__class__.__name__ == "AttackAction"
        except Exception:
            pass

        if is_attack and self._encounter_strip:
            self._step_ready = False  # BLOCK — strip will call release_step()

        def _after_log():
            try:
                self.update_table()
            except Exception:
                pass
            if not self._get_is_running():
                return
            if runner.is_finished:
                if not self._step_ready:
                    # Combat ended during an attack animation — poll until strip is done
                    self._poll_finish_combat()
                else:
                    self._notify_combat_finished()
                return

            if self._step_ready:
                # No animation to wait for — advance immediately
                QTimer.singleShot(50, self.advance_turns)
            # else: BLOCKED — release_step() will call advance_turns()

        self.log_action_result(result, on_complete=_after_log)

    def _poll_finish_combat(self) -> None:
        """Wait for step_ready before finishing combat."""
        if self._step_ready:
            self._notify_combat_finished()
        else:
            QTimer.singleShot(200, self._poll_finish_combat)

    def _notify_combat_finished(self) -> None:
        """Signal the dialog that combat is over."""
        # Clear any remaining queued animations
        if self._encounter_strip:
            self._encounter_strip._queue.clear()
            self._encounter_strip._animating = False
            self._encounter_strip._collapse()
        self._step_ready = True
        if self._on_combat_finished:
            self._on_combat_finished()
        else:
            self.on_session_ended()

    def _center_camera_on_entity(self, entity_name: str) -> None:
        """Smoothly pan the combat map view to center on the named entity."""
        scene = self._get_combat_scene()
        view_fn = self._get_combat_map_view
        if not scene or not view_fn:
            return
        view = view_fn()
        if not view or not hasattr(view, 'smooth_center_on'):
            return
        entity = scene.entity_at_position(entity_name) if hasattr(scene, 'entity_at_position') else None
        # Fall back: look up entity position from the runner
        runner = self._get_runner()
        if runner:
            for e in getattr(runner, '_entities', []):
                if getattr(e, 'name', '') == entity_name:
                    pos = getattr(e, 'position', None)
                    if pos and hasattr(scene, 'get_tile_scene_center'):
                        center = scene.get_tile_scene_center(pos[0], pos[1])
                        if center:
                            view.smooth_center_on(center.x(), center.y())
                    return

    # ------------------------------------------------------------------
    # Session end
    # ------------------------------------------------------------------

    def on_session_ended(
        self,
        *,
        world_positions: dict,
        all_entities: list,
        view_stack,
        combat_map_view,
        combat_scene,
        move_range_outline,
        current_zone: str | None,
        cleared_zones: set,
    ) -> dict:
        """Clean up combat and determine outcome.

        Returns a dict with keys that the dialog needs to apply:
        ``combat_map_view``, ``combat_scene``, ``move_range_outline``,
        ``cleared_zones``.
        """
        self._set_is_running(False)
        self._action_bar.hide()
        self._move_btn.hide()

        animator = self._get_animator()
        if animator:
            animator.cleanup()
            self._set_animator(None)

        # Restore world positions and tear down combat grid
        if world_positions:
            for e in all_entities:
                if e.name in world_positions:
                    e.position = world_positions[e.name]
            world_positions.clear()
        # Hide combat view (kept alive for reuse on next combat)
        if combat_map_view:
            combat_map_view.hide()
        if move_range_outline:
            move_range_outline.clear()
            move_range_outline = None
        if combat_scene:
            combat_scene.clear_all_overlays()
            combat_scene.clear_path_preview()

        runner = self._get_runner()
        state = runner.get_state()
        players_alive = any(
            es.hp > 0 for es in state.entities if es.entity_type == "player")
        enemies_alive = any(
            es.hp > 0 for es in state.entities if es.entity_type == "enemy")

        result = {
            "combat_map_view": combat_map_view,
            "combat_scene": combat_scene,
            "move_range_outline": move_range_outline,
        }

        if players_alive and not enemies_alive:
            if current_zone:
                cleared_zones.add(current_zone.strip().lower())
                msg = f"=== VICTORY! {current_zone} cleared. ==="
            else:
                msg = "=== VICTORY! All enemies defeated. ==="
            if hasattr(self._log, "add_system_message"):
                self._log.add_system_message(msg, "combat")
            else:
                self._log.append(f"\n{msg}")
            self._turn_label.setText("Victory! Returning to exploration...")
            if self._run_transition:
                self._run_transition(
                    "combat_to_exploration_victory",
                    on_complete=self._on_enter_exploration)
            else:
                # Victory sound handled by SoundEventBridge (COMBAT_ENDED)
                QTimer.singleShot(1500, self._on_enter_exploration)
            result["outcome"] = "victory"
        elif enemies_alive and not players_alive:
            self._set_play_state(PlayState.ENDED)
            self._turn_label.setText("DEFEAT. The party has fallen.")
            self._turn_label.setStyleSheet(
                "font-size: 18px; font-weight: bold; padding: 8px; color: #dc2626;"
            )
            self._initiative_section.set_open(False)
            if hasattr(self._log, "add_system_message"):
                self._log.add_system_message("=== DEFEAT ===", "combat")
            else:
                self._log.append("\n=== DEFEAT ===")
            if self._run_transition:
                self._run_transition("combat_to_exploration_defeat")
            # Defeat sound handled by SoundEventBridge (COMBAT_ENDED)
            result["outcome"] = "defeat"
        else:
            self._set_play_state(PlayState.ENDED)
            self._turn_label.setText("Session ended.")
            self._initiative_section.set_open(False)
            result["outcome"] = "ended"

        return result

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log_action_result(self, result, on_complete=None) -> None:
        """Log the outcome of a combat action and trigger animations.

        If *on_complete* is provided it is called after the longest animation
        finishes (or immediately for non-animated actions).
        """
        if not result or not result.action:
            if on_complete:
                QTimer.singleShot(50, on_complete)
            return
        action = result.action
        actor_name = getattr(getattr(action, "actor", None), "name", "?")
        action_type = action.__class__.__name__
        execution_log = list(getattr(result, "execution_log", []))

        # Structured logging when CombatLogWidget is available
        if hasattr(self._log, "add_entry"):
            # Determine round number from initiative tracker
            round_num = 0
            runner = self._get_runner()
            if runner:
                initiative = getattr(getattr(runner, 'session', None), '_initiative', None)
                if initiative:
                    round_num = getattr(initiative, 'round_number', 0)
            is_ai = not (runner and runner.is_player_turn()) if runner else True
            self._log.add_entry(
                actor_name=actor_name,
                action_type=action_type,
                success=result.success,
                execution_log=execution_log,
                round_num=round_num,
                is_ai=is_ai,
            )
        else:
            status = "OK" if result.success else "FAIL"
            self._log.append(f"  {actor_name}: {action_type} [{status}]")
            for line in execution_log:
                self._log.append(f"    {line}")

        # Try choreographer first (multi-phase sequenced animations)
        animation_started = False
        if self._get_choreographer:
            choreographer = self._get_choreographer()
            if choreographer:
                started = choreographer.play(
                    result,
                    done_callback=on_complete,
                    camera_pan_fn=self._center_camera_on_entity,
                    update_table_fn=self.update_table,
                )
                if started:
                    animation_started = True

        # Legacy path: direct animator calls (fallback when no choreographer)
        animator = self._get_animator()
        if not animation_started and animator and action_type == "AttackAction":
            target = getattr(action, "target", None)
            actor = getattr(action, "actor", None)
            if target:
                target_pos = getattr(target, "position", None) or (0, 0)
                source_pos = getattr(actor, "position", None) if actor else None
                log_text = " ".join(getattr(result, "execution_log", []))
                if result.success and "miss" not in log_text.lower():
                    damage = 0
                    for line in getattr(result, "execution_log", []):
                        if "damage" in line.lower():
                            nums = re.findall(r'\d+', line)
                            if nums:
                                damage = int(nums[0])
                                break
                    if damage == 0:
                        damage = getattr(action, '_last_damage', 0) or 5
                    is_crit = "critical" in log_text.lower()
                    animator.on_damage(
                        target.name, target_pos, damage,
                        is_crit=is_crit, source_pos=source_pos,
                        done_callback=on_complete)
                    animation_started = True
                    # Sound: attack hit or crit
                    try:
                        snd = UISoundManager.instance()
                        if is_crit:
                            snd.play("crit", SoundCategory.COMBAT)
                        else:
                            snd.play("attack", SoundCategory.COMBAT)
                    except Exception:
                        pass
                else:
                    animator.on_miss(target.name, target_pos,
                                     done_callback=on_complete)
                    animation_started = True
                    try:
                        UISoundManager.instance().play("miss", SoundCategory.COMBAT)
                    except Exception:
                        pass

        # Sound for spell actions (only if choreographer didn't handle it)
        if not animation_started and action_type == "SpellAction":
            try:
                UISoundManager.instance().play("spell", SoundCategory.COMBAT)
            except Exception:
                pass

        # For non-animated actions, fire on_complete after a brief pause
        if not animation_started and on_complete:
            QTimer.singleShot(100, on_complete)

    # ------------------------------------------------------------------
    # Initiative table
    # ------------------------------------------------------------------

    def update_table(self) -> None:
        """Refresh the initiative panel and map scenes from runner state."""
        runner = self._get_runner()
        if not runner:
            return
        info_filter = self._get_info_filter()

        current_name = runner.current_entity_name() if runner else None
        try:
            initiative = runner.session._initiative
            entries = []
            for e in initiative._entries:
                entity = e.entity_ref
                from ui.animations.portrait_resolver import resolve_portrait
                from pathlib import Path
                _base = str(Path(__file__).resolve().parent.parent.parent)
                entry = {
                    "name": e.entity_name,
                    "roll": e.roll,
                    "entity_type": getattr(entity, "entity_type", ""),
                    "portrait_path": resolve_portrait(entity, base_dir=_base) if entity else None,
                }
                # Role-based HP visibility
                if info_filter.can_see_hp(e.entity_name):
                    entry["hp"] = getattr(entity, "hp", 0)
                    entry["max_hp"] = getattr(entity, "max_hp", 0)
                else:
                    from core.engine.info_filter import InfoFilter
                    hp = getattr(entity, "hp", 0)
                    max_hp = getattr(entity, "max_hp", 1) or 1
                    entry["health_category"] = InfoFilter.health_category(hp, max_hp)
                entries.append(entry)

            self._initiative_panel.set_initiative_order(entries)
            if current_name:
                self._initiative_panel.set_current_turn(
                    current_name, initiative.round_number)
        except Exception:
            pass

        # Update active combat scene (or world map) with role-aware vision
        vision = info_filter.get_vision_entities(
            runner.entities) if info_filter.should_fog() else None
        combat_scene = self._get_combat_scene()
        map_scene = self._get_map_scene()
        mini_map_scene = self._get_mini_map_scene()
        active_scene = combat_scene or map_scene
        active_scene.update_entities(
            runner.entities, current_name, vision_entities=vision)
        mini_map_scene.update_entities(
            runner.entities, current_name, vision_entities=vision)

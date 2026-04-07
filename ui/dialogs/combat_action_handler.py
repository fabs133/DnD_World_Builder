"""Combat action handler — routes player combat actions (attack, spell, move, etc.).

Extracted from PlaySessionDialog to reduce its size.  Receives all
dependencies via the constructor; does NOT hold a back-reference to the dialog.
"""

from __future__ import annotations

import heapq
from typing import TYPE_CHECKING

from core.engine.actions.end_turn_action import EndTurnAction
from core.engine.actions.attack_action import AttackAction
from core.engine.actions.move_action import MoveAction
from core.engine.actions.dash_action import DashAction
from core.engine.actions.dodge_action import DodgeAction
from core.engine.actions.disengage_action import DisengageAction
from core.engine.actions.help_action import HelpAction
from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
from core.engine.play_state import PlayState
from models.entities.entity_type import EntityType

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QLabel, QTextEdit, QPushButton, QWidget
    from core.engine.ui_adapter import UIInputAdapter
    from ui.combat.action_bar_panel import ActionBarPanel
    from ui.combat.play_map_widget import PlayMapScene


class CombatActionHandler:
    """Routes player combat actions: attack, spell, dash, move, end-turn, etc.

    The handler never touches widget *creation* or layout — only
    updates widgets that are handed to it.
    """

    def __init__(
        self,
        *,
        get_play_state,
        get_ui_adapter,
        get_combat_scene,
        turn_label: "QLabel",
        log: "QTextEdit",
        action_bar: "ActionBarPanel",
        move_btn: "QPushButton",
        find_entity,
        parent_widget: "QWidget | None" = None,
    ):
        self._get_play_state = get_play_state
        self._get_ui_adapter = get_ui_adapter
        self._get_combat_scene = get_combat_scene

        # Widgets
        self._turn_label = turn_label
        self._log = log
        self._action_bar = action_bar
        self._move_btn = move_btn

        # Callbacks
        self._find_entity = find_entity
        self._parent_widget = parent_widget

        # Interaction state
        self._current_entity_name: str = ""
        self._current_state = None
        self._current_available: list[str] = []
        self._target_selection_mode = False
        self._movement_mode = False
        self._pending_spell = None
        self._move_range_outline = None
        self._combat_overlay = None

    # ------------------------------------------------------------------
    # Properties for dialog to read/write
    # ------------------------------------------------------------------

    @property
    def current_entity_name(self) -> str:
        return self._current_entity_name

    @current_entity_name.setter
    def current_entity_name(self, value: str):
        self._current_entity_name = value

    @property
    def target_selection_mode(self) -> bool:
        return self._target_selection_mode

    @target_selection_mode.setter
    def target_selection_mode(self, value: bool):
        self._target_selection_mode = value

    @property
    def movement_mode(self) -> bool:
        return self._movement_mode

    @movement_mode.setter
    def movement_mode(self, value: bool):
        self._movement_mode = value

    @property
    def move_range_outline(self):
        return self._move_range_outline

    @move_range_outline.setter
    def move_range_outline(self, value):
        self._move_range_outline = value

    # ------------------------------------------------------------------
    # Action request (from UIInputAdapter)
    # ------------------------------------------------------------------

    def on_action_requested(self, entity_name: str, game_state,
                            available_actions: list) -> None:
        """Called when UIInputAdapter needs a player decision."""
        self._current_entity_name = entity_name
        self._current_state = game_state
        self._current_available = available_actions

        actor = self._find_entity(entity_name)

        action_ids = {
            "ATTACK": "attack", "DASH": "dash", "DODGE": "dodge",
            "DISENGAGE": "disengage", "HELP": "help", "CAST_SPELL": "cast_spell",
        }
        actions_list = []
        for avail_id, bar_id in action_ids.items():
            actions_list.append({"id": bar_id, "enabled": avail_id in available_actions})

        hud_data = {
            "movement_remaining": getattr(actor, "movement_remaining", 0) if actor else 0,
            "movement_max": getattr(actor, "speed", 30) if actor else 30,
            "actions": actions_list,
            "bonus_actions": [],
            "reaction_available": True,
            "spell_slots": getattr(actor, "spell_slots", {}) if actor else {},
        }
        self._action_bar.update_from_hud(hud_data)
        self._action_bar.set_your_turn(True, entity_name)
        self._action_bar.show()

        self._move_btn.setEnabled("MOVE" in available_actions)
        self._move_btn.show()

        # Show movement range overlay on the combat grid
        self._show_combat_movement_range(actor)

    def _show_combat_movement_range(self, actor) -> None:
        """Show pulsing dashed border at movement range edge."""
        combat_scene = self._get_combat_scene()
        if not combat_scene or not actor:
            return
        # Clear previous range outline
        if not self._move_range_outline:
            from ui.combat.play_map_widget import RangeOutline
            self._move_range_outline = RangeOutline(
                combat_scene, combat_scene._tile_size)
        self._move_range_outline.clear()

        pos = getattr(actor, "position", None)
        budget = getattr(actor, "movement_remaining", 0)
        if not pos or budget <= 0:
            return
        tiles_range = budget // 5
        pr, pc = pos[0], pos[1]
        reachable = set()
        for dr in range(-tiles_range, tiles_range + 1):
            for dc in range(-tiles_range, tiles_range + 1):
                if max(abs(dr), abs(dc)) <= tiles_range:
                    r, c = pr + dr, pc + dc
                    tile = combat_scene._tiles.get((r, c))
                    if tile and tile.isVisible():
                        reachable.add((r, c))
        self._move_range_outline.show(
            reachable, combat_scene._tiles, "#378ADD")

    # ------------------------------------------------------------------
    # Action bar dispatch
    # ------------------------------------------------------------------

    def on_action_bar_action(self, action_id: str) -> None:
        ui_adapter = self._get_ui_adapter()
        if not ui_adapter:
            return
        loop = getattr(ui_adapter, "_loop", None)
        if not loop or not loop.isRunning():
            return
        actor = self._find_entity(self._current_entity_name)
        if not actor:
            self.on_end_turn()
            return

        action = None
        if action_id == "attack":
            # Enter target selection mode — user clicks enemy on map
            self._target_selection_mode = True
            self._turn_label.setText("Click an enemy on the map to target")
            self._turn_label.setStyleSheet(
                "font-size: 16px; font-weight: bold; padding: 6px; color: #dc2626;")
            return
        elif action_id == "dash":
            action = DashAction(actor)
        elif action_id == "dodge":
            action = DodgeAction(actor)
        elif action_id == "disengage":
            action = DisengageAction(actor)
        elif action_id == "help":
            action = HelpAction(actor)

        if action:
            self._action_bar.hide()
            self._move_btn.hide()
            ui_adapter.submit_action(action)

    def on_move(self) -> None:
        self._movement_mode = True
        self._turn_label.setText("Click a tile on the map to move there")
        self._turn_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 6px; color: #378add;")

    # ------------------------------------------------------------------
    # Combat tile interaction
    # ------------------------------------------------------------------

    def on_combat_tile_clicked(self, row: int, col: int) -> None:
        """Handle tile click on the combat grid for targeting or movement."""
        combat_scene = self._get_combat_scene()
        if combat_scene:
            combat_scene.clear_path_preview()
        if self._target_selection_mode:
            self._target_selection_mode = False
            if not combat_scene:
                return
            target_entity = combat_scene.entity_at(row, col)
            if not target_entity:
                self._log.append("  No entity at that position.")
                self._turn_label.setText(f"Your turn: {self._current_entity_name}")
                self._turn_label.setStyleSheet(
                    "font-size: 16px; font-weight: bold; padding: 6px; color: #c9952a;")
                return
            etype = getattr(target_entity, "entity_type", "")
            if etype not in (EntityType.ENEMY, EntityType.MONSTER, EntityType.HOSTILE):
                self._log.append(f"  {target_entity.name} is not an enemy.")
                self._turn_label.setText(f"Your turn: {self._current_entity_name}")
                self._turn_label.setStyleSheet(
                    "font-size: 16px; font-weight: bold; padding: 6px; color: #c9952a;")
                return
            actor = self._find_entity(self._current_entity_name)
            if not actor:
                return
            # Check if this is spell targeting or attack targeting
            pending_spell = self._pending_spell
            if pending_spell:
                from models.flow.action.spell_action import SpellAction
                action = SpellAction(
                    caster=actor, spell=pending_spell, targets=[target_entity])
                self._pending_spell = None
            else:
                damage_expr, to_hit_bonus = HeuristicAIAdapter._get_attack_stats(actor)
                action = AttackAction(
                    actor=actor, target=target_entity, weapon_range=5,
                    damage_expr=damage_expr, to_hit_bonus=to_hit_bonus,
                )
            self._action_bar.hide()
            self._move_btn.hide()
            self._get_ui_adapter().submit_action(action)
            return

        if self._movement_mode:
            self._movement_mode = False
            actor = self._find_entity(self._current_entity_name)
            if not actor:
                return
            action = MoveAction(actor=actor, target_position=(row, col))
            self._action_bar.hide()
            self._move_btn.hide()
            if self._combat_overlay:
                self._combat_overlay.clear_movement_range()
            self._get_ui_adapter().submit_action(action)
            return

    def on_combat_tile_hovered(self, row: int, col: int) -> None:
        """Show A* path preview when hovering a tile during combat."""
        combat_scene = self._get_combat_scene()
        if not combat_scene or self._get_play_state() != PlayState.COMBAT:
            return
        actor = self._find_entity(self._current_entity_name)
        if not actor or not getattr(actor, "position", None):
            combat_scene.clear_path_preview()
            return
        target = (row, col)
        if target == tuple(actor.position):
            combat_scene.clear_path_preview()
            return
        # Simple A* on combat grid
        path = self._combat_grid_find_path(actor.position, target)
        if path:
            speed_tiles = getattr(actor, "movement_remaining",
                                  getattr(actor, "speed", 30)) // 5
            in_range = (len(path) - 1) <= speed_tiles
            combat_scene.show_path_preview(path, in_range)
        else:
            combat_scene.clear_path_preview()

    def _combat_grid_find_path(self, start, goal):
        """A* on the combat grid, respecting blocked tiles and occupancy."""
        combat_scene = self._get_combat_scene()
        if not combat_scene:
            return None
        tiles = combat_scene._tiles
        entity_pos = combat_scene._entity_positions
        if goal not in tiles:
            return None
        # Check blocked by terrain tags
        goal_tile_dict = combat_scene._tile_dict_by_pos.get(goal, {})
        goal_tags = goal_tile_dict.get("tags", [])
        if "BLOCKS_MOVEMENT" in goal_tags:
            return None
        # Check occupancy (can't end on another entity)
        if goal in entity_pos and entity_pos[goal].name != self._current_entity_name:
            return None

        def blocked(pos):
            if pos not in tiles:
                return True
            td = combat_scene._tile_dict_by_pos.get(pos, {})
            if "BLOCKS_MOVEMENT" in td.get("tags", []):
                return True
            if pos in entity_pos and pos != start:
                return True
            return False

        counter = 0
        open_set = [(0, counter, start)]
        came_from = {}
        g_score = {start: 0}
        while open_set:
            _, _, current = heapq.heappop(open_set)
            if current == goal:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return path
            cr, cc = current
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nb = (cr + dr, cc + dc)
                    if blocked(nb):
                        continue
                    tentative = g_score[current] + 1
                    if tentative < g_score.get(nb, float("inf")):
                        came_from[nb] = current
                        g_score[nb] = tentative
                        h = max(abs(nb[0] - goal[0]), abs(nb[1] - goal[1]))
                        counter += 1
                        heapq.heappush(open_set, (tentative + h, counter, nb))
        return None

    # ------------------------------------------------------------------
    # End turn
    # ------------------------------------------------------------------

    def on_end_turn(self) -> None:
        """Submit EndTurnAction and reset interaction modes."""
        # Guard: only submit if the UIInputAdapter is actually blocking for input.
        ui_adapter = self._get_ui_adapter()
        if not ui_adapter:
            return
        loop = getattr(ui_adapter, "_loop", None)
        if not loop or not loop.isRunning():
            return
        self._target_selection_mode = False
        self._movement_mode = False
        combat_scene = self._get_combat_scene()
        if combat_scene:
            combat_scene.clear_all_overlays()
            combat_scene.clear_path_preview()
        if self._move_range_outline:
            self._move_range_outline.clear()
        self._action_bar.hide()
        self._move_btn.hide()
        actor = self._find_entity(self._current_entity_name)
        try:
            from core.audio.ui_sound_manager import UISoundManager, SoundCategory
            UISoundManager.instance().play("end_turn", SoundCategory.COMBAT)
        except Exception:
            pass
        ui_adapter.submit_action(EndTurnAction(actor=actor))

    # ------------------------------------------------------------------
    # Spell casting
    # ------------------------------------------------------------------

    def on_spell_cast(self) -> None:
        actor = self._find_entity(self._current_entity_name)
        if not actor:
            return

        spells = getattr(actor, "spells", [])
        spell_slots = getattr(actor, "spell_slots", {})
        if not spells:
            self._log.append("  No spells available!")
            return

        try:
            from ui.combat.spell_selector_dialog import SpellSelectorDialog
            dlg = SpellSelectorDialog(spells, spell_slots, parent=self._parent_widget)
            dlg.spell_selected.connect(self._on_spell_selected)
            dlg.exec_()
        except Exception as e:
            self._log.append(f"  Spell casting error: {e}")

    def _on_spell_selected(self, spell_data: dict) -> None:
        actor = self._find_entity(self._current_entity_name)
        if not actor:
            return

        # Build a Spell object from the dict data
        from models.spell import Spell
        spell = Spell(
            name=spell_data.get("name", "Unknown"),
            level=spell_data.get("level", 0),
            school=spell_data.get("school", ""),
            casting_time=spell_data.get("casting_time", "1 action"),
            range=spell_data.get("range"),
            description=spell_data.get("desc", spell_data.get("description", "")),
            damage=spell_data.get("damage"),
            healing=spell_data.get("healing"),
            effect=spell_data.get("effect"),
        )

        # Determine target: self spells target caster, others need a target
        spell_range_str = str(spell_data.get("range", "")).lower()
        if spell_range_str == "self" or spell.healing:
            targets = [actor]
        else:
            # Enter target selection mode for the spell
            self._pending_spell = spell
            self._target_selection_mode = True
            self._turn_label.setText("Click an enemy to target with spell")
            self._turn_label.setStyleSheet(
                "font-size: 16px; font-weight: bold; padding: 6px; color: #7f77dd;")
            return

        from models.flow.action.spell_action import SpellAction
        action = SpellAction(caster=actor, spell=spell, targets=targets)
        self._action_bar.hide()
        self._move_btn.hide()
        self._get_ui_adapter().submit_action(action)

"""Exploration controller — handles exploration-mode actions and NPC interaction.

Extracted from PlaySessionDialog to reduce its size.  Receives all
dependencies via the constructor; does NOT hold a back-reference to the dialog.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt, QTimer

from core.audio.ui_sound_manager import UISoundManager, SoundCategory
from core.engine.play_state import PlayState, PlayerRole
from core.engine.info_filter import InfoFilter
from models.entities.entity_type import EntityType

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QLabel, QTextEdit, QWidget
    from ui.panels.party_status_strip import PartyStatusStrip


class ExplorationController:
    """Handles exploration movement, skill checks, resting, and NPC interaction.

    The controller never touches widget *creation* or layout — only
    updates widgets that are handed to it.
    """

    def __init__(
        self,
        *,
        get_play_state,
        role: PlayerRole,
        get_all_entities,
        tile_dicts: list[dict],
        zone_map: dict,
        get_current_zone,
        set_current_zone,
        cleared_zones: set,
        get_current_tile_pos,
        set_current_tile_pos,
        selected_character,
        info_filter: InfoFilter,
        turn_label: "QLabel",
        log: "QTextEdit",
        log_section,
        zone_detail,
        map_scene,
        mini_map_scene,
        party_strip: "PartyStatusStrip",
        find_entity,
        enter_combat,
        load_tile_at,
        refit_maps=None,
    ):
        self._get_play_state = get_play_state
        self._role = role
        self._get_all_entities = get_all_entities
        self._tile_dicts = tile_dicts
        self._zone_map = zone_map
        self._get_current_zone = get_current_zone
        self._set_current_zone = set_current_zone
        self._cleared_zones = cleared_zones
        self._get_current_tile_pos = get_current_tile_pos
        self._set_current_tile_pos = set_current_tile_pos
        self._selected_character = selected_character
        self._info_filter = info_filter

        # Widgets
        self._turn_label = turn_label
        self._log = log
        self._log_section = log_section
        self._zone_detail = zone_detail
        self._map_scene = map_scene
        self._mini_map_scene = mini_map_scene
        self._party_strip = party_strip

        # Callbacks
        self._find_entity = find_entity
        self._enter_combat = enter_combat
        self._load_tile_at = load_tile_at
        self._refit_maps = refit_maps

        # Exploration state
        self._combat_cooldown = False

    # ------------------------------------------------------------------
    # Movement
    # ------------------------------------------------------------------

    def get_active_character(self):
        """Get the character for skill checks and exploration actions.

        Player mode: the controlled character.
        DM mode: first player entity.
        """
        if self._selected_character:
            return self._selected_character
        party = [e for e in self._get_all_entities()
                 if e.entity_type == "player"]
        return party[0] if party else None

    def on_explore_move(self, row: int, col: int) -> None:
        """Handle single-click tile movement in exploration mode."""
        if self._get_play_state() != PlayState.EXPLORATION:
            return
        if self._role == PlayerRole.SPECTATOR:
            return

        pos = (row, col)
        self._combat_cooldown = False

        if self._role == PlayerRole.DM:
            # DM mode: move all player entities together
            party = [e for e in self._get_all_entities()
                     if e.entity_type == "player"]
            for p in party:
                p.position = pos
            track_name = party[0].name if party else None
        elif self._selected_character:
            self._selected_character.position = pos
            track_name = self._selected_character.name
            # Also update the matching entity in _all_entities (may be a
            # different object than _selected_character)
            for e in self._get_all_entities():
                if getattr(e, "name", "") == track_name:
                    e.position = pos
        else:
            return

        # Detect zone transitions
        from core.engine.zone_utils import get_zone_at
        new_zone = get_zone_at(self._zone_map, pos)
        if new_zone and new_zone != self._get_current_zone():
            if hasattr(self._log, "add_system_message"):
                self._log.add_system_message(f"Entering zone: {new_zone}", "explore")
            else:
                self._log.append(f"Entering zone: {new_zone}")
            try:
                UISoundManager.instance().play("zone_enter", SoundCategory.UI)
            except Exception:
                pass
        self._set_current_zone(new_zone)

        # Refresh both maps
        all_entities = self._get_all_entities()
        vision = self._info_filter.get_vision_entities(all_entities)
        fog = self._info_filter.should_fog()
        vision_arg = vision if fog else None
        self._map_scene.update_entities(
            all_entities, track_name, vision_entities=vision_arg)
        self._mini_map_scene.update_entities(
            all_entities, track_name, vision_entities=vision_arg)
        # Force scene repaint so newly revealed tiles show immediately
        self._map_scene.invalidate()
        self._mini_map_scene.invalidate()
        # Refit map views for newly revealed tiles
        if self._refit_maps:
            self._refit_maps()

        # Update detail view for new tile
        self._load_tile_at(pos)

        # Check hostile proximity
        leader = self.get_active_character()
        if leader:
            self.check_encounter(leader, pos)

    def check_encounter(self, entity, pos: tuple) -> None:
        """After exploration move, check for nearby hostiles (zone-aware)."""
        if self._combat_cooldown:
            return

        from core.engine.zone_utils import get_zone_at, has_any_zones

        current_zone = get_zone_at(self._zone_map, pos)
        self._set_current_zone(current_zone)

        # Skip zones that have already been cleared
        if current_zone and current_zone.strip().lower() in self._cleared_zones:
            return

        for e in self._get_all_entities():
            if getattr(e, "entity_type", "") != "enemy":
                continue
            if getattr(e, "hp", 0) <= 0:
                continue
            epos = getattr(e, "position", None)
            if not epos:
                continue

            # Zone filter: when zones exist, only same-zone enemies trigger
            if has_any_zones(self._zone_map):
                enemy_zone = get_zone_at(self._zone_map, epos)
                if enemy_zone != current_zone:
                    continue

            if abs(epos[0] - pos[0]) + abs(epos[1] - pos[1]) <= 2:
                if hasattr(self._log, "add_system_message"):
                    self._log.add_system_message("Hostile encounter! Rolling initiative...", "combat")
                else:
                    self._log.append("Hostile encounter! Rolling initiative...")
                try:
                    UISoundManager.instance().play_shared("combat_start", SoundCategory.ALERT)
                except Exception:
                    pass
                QTimer.singleShot(300, self._enter_combat)
                return

    @property
    def combat_cooldown(self) -> bool:
        return self._combat_cooldown

    @combat_cooldown.setter
    def combat_cooldown(self, value: bool):
        self._combat_cooldown = value

    # ------------------------------------------------------------------
    # Exploration actions
    # ------------------------------------------------------------------

    def refresh_party_strip(self) -> None:
        """Update the party status strip from current entity data."""
        players = [e for e in self._get_all_entities()
                   if e.entity_type == "player"]
        self._party_strip.set_party([
            {"name": p.name, "hp": p.hp, "max_hp": p.max_hp} for p in players
        ])

    def on_exploration_action(self, action_id: str) -> None:
        if action_id == "interact":
            # Use the currently selected entity in the detail list
            item = self._zone_detail._entity_list.currentItem()
            if item:
                entity = item.data(Qt.UserRole)  # entity object
                if entity is not None:
                    self.on_entity_clicked(entity)
                    return
            self._log.append("  Select an entity in the detail view to interact.")
        elif action_id == "search":
            self._do_search_check()
        elif action_id == "sneak":
            self._do_sneak_check()

    def _do_search_check(self) -> None:
        try:
            UISoundManager.instance().play("dice", SoundCategory.COMBAT)
        except Exception:
            pass
        entity = self.get_active_character()
        if not entity:
            self._log.append("  No character selected.")
            return
        wis_mod = (entity.stats.get("Wisdom", 10) - 10) // 2
        roll = random.randint(1, 20)
        total = roll + wis_mod
        self._log.append(
            f"  {entity.name} searches: d20({roll}) + WIS({wis_mod:+d}) = {total}")

        pos = self._get_current_tile_pos()
        found = False

        if pos:
            # Check for items, traps, and objects at this tile
            for e in self._get_all_entities():
                if getattr(e, "position", None) != pos:
                    continue
                et = getattr(e, "entity_type", "")
                if et == EntityType.TRAP:
                    dc = getattr(e, "stats", {}).get("perception_dc", 15)
                    if total >= dc:
                        self._log.append(f"  You spot a {e.name}! (DC {dc})")
                        found = True
                elif et in (EntityType.ITEM, EntityType.OBJECT):
                    if total >= 10:
                        desc = getattr(e, "note", "") or ""
                        if desc:
                            self._log.append(f"  You find: {e.name} — {desc}")
                        else:
                            self._log.append(f"  You find: {e.name}")
                        found = True

            # Check tile note for environmental details
            for td in self._tile_dicts:
                if tuple(td.get("position", [0, 0])) == pos:
                    note = td.get("note") or ""
                    if note and total >= 12:
                        self._log.append(f"  You observe: {note}")
                        found = True
                    tags = td.get("tags", [])
                    if "TRAP_ZONE" in tags and total >= 14:
                        self._log.append("  You detect a trap mechanism in this area!")
                        found = True
                    break

        if not found:
            if total >= 15:
                self._log.append("  The area appears safe. Nothing hidden.")
            elif total >= 10:
                self._log.append("  Nothing obvious stands out.")
            else:
                self._log.append("  You fail to notice anything of interest.")

    def _do_sneak_check(self) -> None:
        try:
            UISoundManager.instance().play("dice", SoundCategory.COMBAT)
        except Exception:
            pass
        entity = self.get_active_character()
        if not entity:
            self._log.append("  No character selected.")
            return
        dex_mod = (entity.stats.get("Dexterity", 10) - 10) // 2
        roll = random.randint(1, 20)
        total = roll + dex_mod
        self._log.append(
            f"  {entity.name} sneaks: d20({roll}) + DEX({dex_mod:+d}) = {total}")
        if total >= 15:
            self._log.append("  Moving stealthily!")
        else:
            self._log.append("  You fail to move quietly.")

    def on_rest_requested(self, rest_type: str) -> None:
        if rest_type == "short_rest":
            self._do_short_rest()
        elif rest_type == "long_rest":
            self._do_long_rest()

    def _do_short_rest(self) -> None:
        players = [e for e in self._get_all_entities()
                   if e.entity_type == "player" and e.is_alive]
        if hasattr(self._log, "add_system_message"):
            self._log.add_system_message("=== Short Rest (1 hour) ===", "explore")
        else:
            self._log.append("=== Short Rest (1 hour) ===")
        for p in players:
            if p.hp < p.max_hp:
                heal_amount = max(1, p.max_hp // 4)
                actual = p.heal(heal_amount)
                if actual > 0:
                    self._log.append(
                        f"  {p.name} recovers {actual} HP ({p.hp}/{p.max_hp})")
        if hasattr(self._log, "add_system_message"):
            self._log.add_system_message("Short rest complete.", "explore")
        else:
            self._log.append("Short rest complete.")
        try:
            UISoundManager.instance().play("save", SoundCategory.UI)
        except Exception:
            pass
        self.refresh_party_strip()

    def _do_long_rest(self) -> None:
        players = [e for e in self._get_all_entities()
                   if e.entity_type == "player" and e.is_alive]
        if hasattr(self._log, "add_system_message"):
            self._log.add_system_message("=== Long Rest (8 hours) ===", "explore")
        else:
            self._log.append("=== Long Rest (8 hours) ===")
        for p in players:
            old_hp = p.hp
            p.hp = p.max_hp
            if p.hp > old_hp:
                self._log.append(
                    f"  {p.name} fully healed ({old_hp} -> {p.max_hp})")
            p.conditions.clear()
            # Recover spell slots
            max_slots = p.stats.get("spell_slots", 0)
            if max_slots and getattr(p, "spell_slots", 0) < max_slots:
                p.spell_slots = max_slots
                self._log.append(f"  {p.name} spell slots restored ({max_slots})")
        if hasattr(self._log, "add_system_message"):
            self._log.add_system_message("Long rest complete. All HP and spell slots restored.", "explore")
        else:
            self._log.append("Long rest complete. All HP restored.")
        self.refresh_party_strip()

    # ------------------------------------------------------------------
    # Entity interaction
    # ------------------------------------------------------------------

    def on_entity_clicked(self, entity_or_name) -> None:
        """Handle click on an entity in the zone detail view.

        *entity_or_name* is a ``GameEntity`` object (from the entity list) or
        a ``str`` name (from the zone canvas).  We normalise to the object.
        """
        if isinstance(entity_or_name, str):
            entity = self._find_entity(entity_or_name)
        else:
            entity = entity_or_name
        if not entity:
            self._log.append(f"  Entity not found: {entity_or_name}")
            return

        name = getattr(entity, "name", str(entity))
        etype = getattr(entity, "entity_type", "")

        # -- Unmissable feedback --
        # 1. Status label (always visible at top)
        self._turn_label.setText(f"Selected: {name} ({etype})")
        self._turn_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 6px; color: #c9952a;")

        # 2. Log summary + ensure log is open + scroll to bottom
        self._log_entity_summary(entity)
        self._log_section.set_open(True)
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())

        # 3. Play NPC interaction sound
        if etype in (EntityType.NPC, EntityType.ALLY, EntityType.COMPANION):
            try:
                UISoundManager.instance().play("npc_talk", SoundCategory.UI)
            except Exception:
                pass

        # 4. Show NPC interaction panel
        interactions = []
        if etype == EntityType.NPC:
            interactions.append({"id": "talk", "label": "Talk"})
            interactions.append({"id": "inspect", "label": "Inspect"})
            if self._role == PlayerRole.DM:
                interactions.append({"id": "stat_block", "label": "View Stats"})
                interactions.append({"id": "edit", "label": "Edit"})
        elif etype in (EntityType.ENEMY, EntityType.MONSTER, EntityType.HOSTILE):
            if self._role == PlayerRole.DM:
                interactions.append({"id": "stat_block", "label": "View Stats"})
                interactions.append({"id": "edit", "label": "Edit"})
            else:
                interactions.append({"id": "inspect", "label": "Observe"})
        elif etype == EntityType.PLAYER:
            interactions.append({"id": "stat_block", "label": "Character Sheet"})
        else:
            interactions.append({"id": "inspect", "label": "Examine"})

        if interactions:
            self._zone_detail.show_npc_panel(name, interactions)
        else:
            self._zone_detail.hide_npc_panel()

    def _log_entity_summary(self, entity) -> None:
        """Log a brief summary of an entity to the event log."""
        name = entity.name
        etype = getattr(entity, "entity_type", "unknown")
        parts = [f"--- {name} ({etype}) ---"]

        if self._info_filter.can_see_hp(name) or etype == EntityType.PLAYER:
            hp = getattr(entity, "hp", "?")
            max_hp = getattr(entity, "max_hp", "?")
            ac = getattr(entity, "armor_class", "?")
            parts.append(f"  HP: {hp}/{max_hp}  AC: {ac}")

        note = getattr(entity, "note", "") or ""
        if note:
            parts.append(f"  {note}")

        personality = getattr(entity, "personality", None)
        if personality and etype == EntityType.NPC:
            trait = getattr(personality, "trait", "") or ""
            bond = getattr(personality, "bond", "") or ""
            flaw = getattr(personality, "flaw", "") or ""
            if trait:
                parts.append(f"  Trait: {trait}")
            if bond:
                parts.append(f"  Bond: {bond}")
            if flaw:
                parts.append(f"  Flaw: {flaw}")

        lines = getattr(entity, "dialogue_lines", {})
        greetings = lines.get("greeting", [])
        if greetings:
            parts.append(f'  Says: "{greetings[0]}"')

        # Fallback: no data at all
        if len(parts) == 1:
            if etype == EntityType.NPC:
                parts.append(f"  {name} regards you silently.")
            elif etype in (EntityType.ITEM, EntityType.OBJECT):
                parts.append(f"  An ordinary {etype}.")
            elif etype in (EntityType.ENEMY, EntityType.MONSTER, EntityType.HOSTILE):
                parts.append("  A hostile creature.")

        for line in parts:
            self._log.append(line)

    def on_entity_info_fallback(self, entity_name: str, entity_type: str) -> None:
        """Independent fallback: log entity info even if entity_clicked chain fails."""
        # Update status label (always visible at the top)
        self._turn_label.setText(f"Selected: {entity_name} ({entity_type})")
        self._turn_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 6px; color: #c9952a;")
        # Ensure log section is visible
        self._log_section.set_open(True)

    def on_interaction_chosen(self, entity_name: str, interaction_id: str,
                              parent_widget=None) -> None:
        """Dispatch an entity interaction to the appropriate dialog."""
        entity = self._find_entity(entity_name)
        if not entity:
            return

        if interaction_id == "talk":
            try:
                from ui.exploration.npc_conversation_dialog import NpcConversationDialog
                # Voice: only use pre-generated files, no on-the-fly generation
                dlg = NpcConversationDialog(
                    entity,
                    parent=parent_widget,
                )
                dlg.exec_()
            except Exception as e:
                self._log.append(f"  Conversation error: {e}")

        elif interaction_id == "stat_block":
            try:
                from ui.dialogs.stat_block_dialog import StatBlockDialog
                dlg = StatBlockDialog(entity, parent=parent_widget)
                dlg.exec_()
            except Exception as e:
                self._log.append(f"  Stat block error: {e}")

        elif interaction_id == "edit":
            try:
                from ui.dialogs.entity_preview_dialog import EntityPreviewDialog
                dlg = EntityPreviewDialog(entity, parent=parent_widget)
                dlg.exec_()
            except Exception as e:
                self._log.append(f"  Entity edit error: {e}")

        elif interaction_id == "inspect":
            # Log role-filtered info and show floating toast
            name = entity.name
            etype = getattr(entity, "entity_type", "unknown")
            if self._info_filter.can_see_hp(name):
                hp = getattr(entity, "hp", "?")
                max_hp = getattr(entity, "max_hp", "?")
                ac = getattr(entity, "armor_class", "?")
                info_line = f"{name} ({etype}) — HP: {hp}/{max_hp}, AC: {ac}"
            else:
                hp = getattr(entity, "hp", 0)
                max_hp = getattr(entity, "max_hp", 1) or 1
                category = InfoFilter.health_category(hp, max_hp)
                info_line = f"{name} ({etype}) — {category}"

            # Add personality/traits if available
            traits = getattr(entity, "personality_traits", None)
            if traits:
                info_line += f"\n{traits}"

            self._log.append(f"  {info_line}")
            # Show prominent toast in the main view
            if hasattr(self._zone_detail, "show_info_toast"):
                self._zone_detail.show_info_toast(info_line)

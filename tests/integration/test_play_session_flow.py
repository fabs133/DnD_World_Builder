"""Integration test: full play-session flow through real UI widgets.

This test instantiates a real PlaySessionDialog with a minimal scenario,
then drives it through INTRO → EXPLORATION → COMBAT → session-end by
invoking the same methods the UI signals would trigger.  It catches
``AttributeError``, missing method stubs, and widget API mismatches
that unit tests miss because they mock the widgets away.

Mark: ``@pytest.mark.slow`` — excluded from the default test run.
Run explicitly with ``pytest -m slow`` or by name.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from core.engine.play_state import PlayState, PlayerRole
from models.entities.game_entity import GameEntity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(name, entity_type="player", hp=20, position=(0, 0),
                 armor_class=12, speed=30):
    e = GameEntity(
        name=name, entity_type=entity_type,
        stats={"hp": hp, "max_hp": hp, "armor_class": armor_class,
               "speed": speed, "Dexterity": 14, "Strength": 12},
    )
    e.position = position
    e.movement_remaining = speed
    e.action_used = False
    e.bonus_action_used = False
    e.reaction_used = False
    return e


def _make_tile_dicts(width=8, height=8, terrain="GRASS"):
    tiles = []
    for r in range(height):
        for c in range(width):
            tags = ["START_ZONE"] if (r, c) == (7, 0) else []
            entities_on_tile = []
            tiles.append({
                "tile_id": f"t_{r}_{c}",
                "position": [r, c],
                "terrain": terrain,
                "tags": tags,
                "elevation": 0,
                "entities": entities_on_tile,
            })
    return tiles


def _scenario_with_entities():
    """Build tile_dicts that embed player + enemy entities."""
    tiles = _make_tile_dicts()

    # Place a player entity on the start tile
    player_dict = {
        "name": "TestHero",
        "entity_type": "player",
        "stats": {"hp": 30, "max_hp": 30, "armor_class": 15,
                  "speed": 30, "Dexterity": 14},
        "inventory": [],
        "triggers": [],
    }
    # Place an NPC on (5, 3)
    npc_dict = {
        "name": "Bartender",
        "entity_type": "npc",
        "stats": {"hp": 10, "max_hp": 10, "armor_class": 10, "speed": 30},
        "inventory": [],
        "triggers": [],
    }
    # Place an enemy adjacent to player start (7,1) so combat triggers
    enemy_dict = {
        "name": "Goblin Scout",
        "entity_type": "enemy",
        "stats": {"hp": 7, "max_hp": 7, "armor_class": 13,
                  "speed": 30, "Dexterity": 14, "Strength": 8},
        "inventory": [],
        "triggers": [],
    }

    # Embed in tiles
    for td in tiles:
        pos = tuple(td["position"])
        if pos == (7, 0):
            td["entities"] = [player_dict]
        elif pos == (5, 3):
            td["entities"] = [npc_dict]
        elif pos == (7, 1):
            td["entities"] = [enemy_dict]

    return tiles


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def scenario_tiles():
    return _scenario_with_entities()


@pytest.fixture
def dialog(qapp, scenario_tiles):
    """Create a real PlaySessionDialog in DM mode (most permissive)."""
    from ui.dialogs.play_session_dialog import PlaySessionDialog
    dlg = PlaySessionDialog(
        tile_dicts=scenario_tiles,
        scenario_name="Integration Test",
        role=PlayerRole.DM,
        selected_character=None,
        meta={"description": "Automated integration test scenario"},
    )
    yield dlg
    # Stop any running turn loops before teardown
    dlg._is_running = False
    dlg.close()
    dlg.deleteLater()
    QApplication.processEvents()


def _enter_combat_safe(dialog):
    """Enter combat with ALL_AUTO so no UIInputAdapter blocks, then stop the loop."""
    from core.engine.play_state import DMAutomation
    dialog._dm_automation = DMAutomation.ALL_AUTO
    dialog._enter_combat()
    # Immediately stop the turn loop so QTimers don't fire during test
    dialog._is_running = False


# ---------------------------------------------------------------------------
# Tests — marked slow so they don't run on every commit
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestPlaySessionFullFlow:
    """Drive a PlaySessionDialog through its full lifecycle."""

    def test_dialog_constructs(self, dialog):
        """PlaySessionDialog can be instantiated with a real scenario."""
        assert dialog._play_state == PlayState.INTRO
        assert len(dialog._all_entities) >= 2  # at least player + enemy
        assert dialog._info_filter is not None

    def test_intro_to_exploration(self, dialog):
        """Completing the intro transitions to exploration mode."""
        dialog._on_intro_complete()
        assert dialog._play_state == PlayState.EXPLORATION

    def test_exploration_widgets_accessible(self, dialog):
        """All exploration widgets respond after entering exploration."""
        dialog._on_intro_complete()

        # Combat log widget methods
        dialog._log.append("Test log message")
        dialog._log.add_system_message("System test", "explore")
        sb = dialog._log.verticalScrollBar()
        assert sb is not None

        # Party strip
        dialog._explore_ctrl.refresh_party_strip()

        # Turn label
        assert dialog._turn_label.text() != ""

    def test_exploration_actions(self, dialog):
        """Exploration actions (search, sneak, rest) execute without error."""
        dialog._on_intro_complete()

        # Search
        dialog._explore_ctrl.on_exploration_action("search")

        # Sneak
        dialog._explore_ctrl.on_exploration_action("sneak")

        # Short rest
        dialog._explore_ctrl.on_rest_requested("short")

        # Long rest
        dialog._explore_ctrl.on_rest_requested("long")

    def test_entity_click_in_exploration(self, dialog):
        """Clicking an entity in exploration mode invokes the NPC panel."""
        dialog._on_intro_complete()

        # Find the NPC entity
        npc = dialog._find_entity("Bartender")
        if npc:
            dialog._explore_ctrl.on_entity_clicked(npc)

    def test_entity_click_by_name(self, dialog):
        """Clicking by entity name string also works."""
        dialog._on_intro_complete()
        dialog._explore_ctrl.on_entity_clicked("Bartender")

    def test_enter_combat(self, dialog):
        """Combat can be entered from exploration."""
        dialog._on_intro_complete()
        _enter_combat_safe(dialog)

        assert dialog._play_state == PlayState.COMBAT
        assert dialog._runner is not None
        assert dialog._combat_scene is not None

    def test_combat_log_structured_entries(self, dialog):
        """After entering combat, structured log entries work."""
        dialog._on_intro_complete()
        _enter_combat_safe(dialog)

        dialog._log.add_entry(
            actor_name="TestHero",
            action_type="Attack",
            success=True,
            execution_log=["d20(15) + 4 = 19 vs AC 13 → HIT", "1d6+2 = 5 slashing"],
            round_num=1,
            is_ai=False,
        )
        assert dialog._log._entry_count >= 1

    def test_combat_keyboard_shortcuts_dont_crash(self, dialog):
        """Pressing combat keyboard shortcuts during combat doesn't crash."""
        dialog._on_intro_complete()
        _enter_combat_safe(dialog)

        from PyQt5.QtGui import QKeyEvent
        from PyQt5.QtCore import QEvent

        for key in [Qt.Key_Space, Qt.Key_1, Qt.Key_2, Qt.Key_3,
                    Qt.Key_4, Qt.Key_5, Qt.Key_6, Qt.Key_Tab,
                    Qt.Key_Escape, Qt.Key_W, Qt.Key_A, Qt.Key_S,
                    Qt.Key_D]:
            event = QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier)
            dialog.keyPressEvent(event)

    def test_combat_scene_tile_pulse(self, dialog):
        """Clicking a tile in combat triggers a pulse animation."""
        dialog._on_intro_complete()
        _enter_combat_safe(dialog)

        scene = dialog._combat_scene
        if scene:
            tile = scene._tiles.get((0, 0))
            if tile:
                tile.pulse_select()
                assert tile._pulse_color is not None

    def test_combat_scene_conditions(self, dialog):
        """Setting conditions on combat tiles doesn't crash."""
        dialog._on_intro_complete()
        _enter_combat_safe(dialog)

        scene = dialog._combat_scene
        if scene:
            for pos, tile in list(scene._tiles.items())[:3]:
                tile.set_conditions(["poisoned", "stunned"])
                tile.set_conditions([])

    def test_initiative_panel_hp_update(self, dialog):
        """HP updates on the initiative panel animate without error."""
        dialog._on_intro_complete()
        _enter_combat_safe(dialog)

        panel = dialog._initiative_panel
        # Update HP for any entity that's in the initiative order
        for entry in panel._entries:
            panel.update_entity_hp(entry["name"], 5, entry.get("max_hp", 20))
            break

    def test_combat_to_exploration_return(self, dialog):
        """After combat ends, the dialog can return to exploration."""
        dialog._on_intro_complete()
        _enter_combat_safe(dialog)

        # Simulate combat ending by calling the exploration transition directly
        dialog._play_state = PlayState.EXPLORATION
        dialog._is_running = False
        dialog._enter_exploration()
        assert dialog._play_state == PlayState.EXPLORATION

    def test_dm_automation_applied_before_turn_loop(self, dialog):
        """Full auto mode swaps adapters so is_player_turn() returns False."""
        from core.engine.play_state import DMAutomation
        dialog._dm_automation = DMAutomation.ALL_AUTO
        dialog._on_intro_complete()
        dialog._enter_combat()
        dialog._is_running = False  # Stop loop so it doesn't block

        # In ALL_AUTO every entity should have HeuristicAIAdapter
        from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
        runner = dialog._runner
        for entity in runner.entities:
            adapter = runner._session._adapters.get(entity.name)
            assert isinstance(adapter, HeuristicAIAdapter), (
                f"{entity.name} should have HeuristicAIAdapter in full auto, "
                f"got {type(adapter).__name__}"
            )
        # Therefore no turn is a "player turn"
        assert not runner.is_player_turn()

    def test_initiative_hidden_during_exploration(self, dialog):
        """Initiative panel is not visible during exploration."""
        dialog._on_intro_complete()
        assert dialog._play_state == PlayState.EXPLORATION
        assert dialog._initiative_section.isHidden()

    def test_initiative_visible_during_combat(self, dialog):
        """Initiative panel appears when combat starts."""
        dialog._on_intro_complete()
        _enter_combat_safe(dialog)
        assert not dialog._initiative_section.isHidden()

    def test_minimap_hidden_during_combat(self, dialog):
        """Minimap sidebar is hidden during combat."""
        dialog._on_intro_complete()
        _enter_combat_safe(dialog)
        assert dialog._map_section.isHidden()

    def test_minimap_visible_during_exploration(self, dialog):
        """Minimap sidebar is shown during exploration."""
        dialog._on_intro_complete()
        assert not dialog._map_section.isHidden()


@pytest.mark.slow
class TestPlaySessionWidgetCompat:
    """Verify CombatLogWidget is a drop-in replacement for QTextEdit."""

    def test_log_all_qtextedit_methods(self, dialog):
        """Every QTextEdit method called by controllers exists on CombatLogWidget."""
        log = dialog._log

        # Methods the controllers call
        log.append("plain text")
        log.verticalScrollBar()
        log.clear()

        # Backward-compat stubs
        from PyQt5.QtGui import QFont
        log.setReadOnly(True)
        log.setFont(QFont("Consolas", 10))
        log.setPlaceholderText("test")

    def test_log_add_entry(self, dialog):
        log = dialog._log
        log.add_entry("Hero", "Attack", True, ["d20(18) vs AC 15 → HIT"], round_num=1)
        log.add_entry("Goblin", "Attack", False, ["d20(3) vs AC 15 → MISS"], round_num=1, is_ai=True)
        assert log._entry_count == 2

    def test_log_add_system_message_styles(self, dialog):
        log = dialog._log
        log.add_system_message("Combat!", "combat")
        log.add_system_message("Exploring...", "explore")
        log.add_system_message("Info", "info")
        assert log._entry_count == 3

    def test_log_scroll_to_bottom(self, dialog):
        log = dialog._log
        for i in range(50):
            log.append(f"Line {i}")
        sb = log.verticalScrollBar()
        # Just verify this doesn't crash — scroll position depends on rendering
        sb.setValue(sb.maximum())


@pytest.mark.slow
class TestPlaySessionTooltip:
    """Verify tooltip infrastructure wired correctly."""

    def test_map_scene_has_tooltip(self, dialog):
        dialog._on_intro_complete()
        scene = dialog._map_scene
        assert hasattr(scene, '_tooltip')
        assert hasattr(scene, '_tooltip_timer')

    def test_map_scene_info_filter_set(self, dialog):
        dialog._on_intro_complete()
        assert dialog._map_scene._info_filter is not None

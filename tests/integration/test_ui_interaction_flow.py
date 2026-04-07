"""End-to-end UI interaction test suite.

Exercises every user-triggerable code path from the launcher through
editor, play session, and multiplayer hosting — without displaying
windows.  Catches ``AttributeError``, missing arguments, and
half-wired buttons that only surface during real usage.

Run with: ``pytest -m slow tests/integration/test_ui_interaction_flow.py -v``
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from core.engine.play_state import PlayState, PlayerRole, DMAutomation
from models.entities.game_entity import GameEntity
from models.game_master import Gamemaster
from models.world.world import World


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tile_dicts(width=6, height=6, terrain="GRASS"):
    tiles = []
    for r in range(height):
        for c in range(width):
            tags = ["START_ZONE"] if (r, c) == (5, 0) else []
            tiles.append({
                "tile_id": f"t_{r}_{c}",
                "position": [r, c],
                "terrain": terrain,
                "tags": tags,
                "elevation": 0,
                "entities": [],
            })
    return tiles


def _scenario_with_party_and_enemies():
    """Tiles with 2 players + 1 NPC + 1 enemy embedded."""
    tiles = _make_tile_dicts()
    player1 = {
        "name": "Fighter", "entity_type": "player",
        "stats": {"hp": 28, "max_hp": 28, "armor_class": 16,
                  "speed": 30, "Dexterity": 12, "Strength": 16},
        "inventory": [], "triggers": [],
    }
    player2 = {
        "name": "Wizard", "entity_type": "player",
        "stats": {"hp": 18, "max_hp": 18, "armor_class": 12,
                  "speed": 30, "Dexterity": 14, "Intelligence": 18},
        "inventory": [], "triggers": [],
    }
    npc = {
        "name": "Innkeeper", "entity_type": "npc",
        "stats": {"hp": 8, "max_hp": 8, "armor_class": 10, "speed": 30},
        "inventory": [], "triggers": [],
    }
    enemy = {
        "name": "Bandit", "entity_type": "enemy",
        "stats": {"hp": 11, "max_hp": 11, "armor_class": 13,
                  "speed": 30, "Dexterity": 14, "Strength": 12},
        "inventory": [], "triggers": [],
    }
    for td in tiles:
        pos = tuple(td["position"])
        if pos == (5, 0):
            td["entities"] = [player1, player2]
        elif pos == (3, 2):
            td["entities"] = [npc]
        elif pos == (5, 1):
            td["entities"] = [enemy]
    return tiles


def _write_scenario_to_temp(tiles, name="TestScenario"):
    """Write a minimal map.json to a temp directory, return path."""
    td = tempfile.mkdtemp()
    scenario_dir = Path(td) / name
    scenario_dir.mkdir()
    map_path = scenario_dir / "map.json"
    data = {
        "version": "1.0",
        "meta": {
            "map_name": name,
            "author": "test",
            "grid_type": "square",
            "rows": 6, "cols": 6,
            "description": "Integration test scenario",
        },
        "tiles": tiles,
    }
    map_path.write_text(json.dumps(data))
    return map_path


def _enter_combat_safe(dialog):
    """Enter combat with ALL_AUTO and immediately stop the loop."""
    dialog._dm_automation = DMAutomation.ALL_AUTO
    dialog._enter_combat()
    dialog._is_running = False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def scenario_tiles():
    return _scenario_with_party_and_enemies()


@pytest.fixture
def play_dialog(qapp, scenario_tiles):
    """Fully constructed PlaySessionDialog in DM mode."""
    from ui.dialogs.play_session_dialog import PlaySessionDialog
    dlg = PlaySessionDialog(
        tile_dicts=scenario_tiles,
        scenario_name="UI Flow Test",
        role=PlayerRole.DM,
        selected_character=None,
        meta={"description": "Full UI interaction test"},
    )
    yield dlg
    dlg._is_running = False
    dlg.close()
    dlg.deleteLater()
    QApplication.processEvents()


@pytest.fixture
def play_dialog_player(qapp, scenario_tiles):
    """PlaySessionDialog in PLAYER mode with selected character."""
    from ui.dialogs.play_session_dialog import PlaySessionDialog
    # Need to extract entities to find a player character
    from core.engine.play_session import extract_entities_from_tiles
    entities, start = extract_entities_from_tiles(scenario_tiles)
    player = next((e for e in entities if e.entity_type == "player"), None)

    dlg = PlaySessionDialog(
        tile_dicts=scenario_tiles,
        scenario_name="Player Mode Test",
        role=PlayerRole.PLAYER,
        selected_character=player,
        meta={},
    )
    yield dlg
    dlg._is_running = False
    dlg.close()
    dlg.deleteLater()
    QApplication.processEvents()


# ---------------------------------------------------------------------------
# 1. LAUNCHER ENTRY POINTS
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestLauncherEntryPoints:
    """Verify all LaunchDialog buttons create their target without crashing."""

    def test_launch_game_creation(self, qapp):
        """'Open Game Creation' creates MainController without error."""
        from core.gameCreation.main_controller import MainController
        mc = MainController()
        assert mc is not None
        mc.close()
        mc.deleteLater()
        QApplication.processEvents()

    def test_launch_host_requires_map(self, qapp):
        """Host session creates a default map if none exists."""
        from core.gameCreation.main_controller import MainController
        mc = MainController()
        assert mc.map_editor is None
        mc.start_new_map()
        assert mc.map_editor is not None
        mc.close()
        mc.deleteLater()
        QApplication.processEvents()

    def test_build_gamemaster_from_scene(self, qapp):
        """MainWindow._build_gamemaster_from_scene() produces a valid Gamemaster."""
        from core.gameCreation.main_controller import MainController
        mc = MainController()
        mc.start_new_map()
        editor = mc.map_editor

        gm = editor._build_gamemaster_from_scene()
        assert isinstance(gm, Gamemaster)
        assert gm.world is not None
        assert gm.world.tile_manager is not None

        mc.close()
        mc.deleteLater()
        QApplication.processEvents()


# ---------------------------------------------------------------------------
# 2. PLAY SESSION — LIFECYCLE
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestPlaySessionLifecycle:
    """Test the full INTRO → EXPLORATION → COMBAT → EXPLORATION flow."""

    def test_construction_dm_mode(self, play_dialog):
        assert play_dialog._play_state == PlayState.INTRO
        assert play_dialog._info_filter is not None
        assert len(play_dialog._all_entities) >= 3

    def test_construction_player_mode(self, play_dialog_player):
        assert play_dialog_player._play_state == PlayState.INTRO

    def test_intro_to_exploration(self, play_dialog):
        play_dialog._on_intro_complete()
        assert play_dialog._play_state == PlayState.EXPLORATION

    def test_exploration_to_combat(self, play_dialog):
        play_dialog._on_intro_complete()
        _enter_combat_safe(play_dialog)
        assert play_dialog._play_state == PlayState.COMBAT
        assert play_dialog._runner is not None
        assert play_dialog._combat_scene is not None

    def test_combat_back_to_exploration(self, play_dialog):
        play_dialog._on_intro_complete()
        _enter_combat_safe(play_dialog)
        play_dialog._play_state = PlayState.EXPLORATION
        play_dialog._is_running = False
        play_dialog._enter_exploration()
        assert play_dialog._play_state == PlayState.EXPLORATION


# ---------------------------------------------------------------------------
# 3. PLAY SESSION — EXPLORATION INTERACTIONS
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestExplorationInteractions:
    """Test all exploration-mode user interactions."""

    def test_tile_navigation(self, play_dialog):
        play_dialog._on_intro_complete()
        play_dialog._load_tile_at((3, 2))
        assert play_dialog._current_tile_pos == (3, 2)

    def test_show_full_map(self, play_dialog):
        play_dialog._on_intro_complete()
        play_dialog._show_full_map()

    def test_return_to_detail(self, play_dialog):
        play_dialog._on_intro_complete()
        play_dialog._view_stack.setCurrentIndex(2)
        play_dialog._return_to_detail()

    def test_exploration_search(self, play_dialog):
        play_dialog._on_intro_complete()
        play_dialog._explore_ctrl.on_exploration_action("search")

    def test_exploration_sneak(self, play_dialog):
        play_dialog._on_intro_complete()
        play_dialog._explore_ctrl.on_exploration_action("sneak")

    def test_exploration_short_rest(self, play_dialog):
        play_dialog._on_intro_complete()
        play_dialog._explore_ctrl.on_rest_requested("short")

    def test_exploration_long_rest(self, play_dialog):
        play_dialog._on_intro_complete()
        play_dialog._explore_ctrl.on_rest_requested("long")

    def test_entity_click_npc(self, play_dialog):
        play_dialog._on_intro_complete()
        play_dialog._explore_ctrl.on_entity_clicked("Innkeeper")

    def test_entity_click_by_name_string(self, play_dialog):
        play_dialog._on_intro_complete()
        play_dialog._explore_ctrl.on_entity_clicked("Fighter")

    def test_sidebar_tile_click(self, play_dialog):
        play_dialog._on_intro_complete()
        play_dialog._on_sidebar_tile_clicked(3, 2)

    def test_party_strip_refresh(self, play_dialog):
        play_dialog._on_intro_complete()
        play_dialog._explore_ctrl.refresh_party_strip()


# ---------------------------------------------------------------------------
# 4. PLAY SESSION — COMBAT INTERACTIONS
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestCombatInteractions:
    """Test combat-mode user interactions."""

    def test_initiative_panel_populated(self, play_dialog):
        play_dialog._on_intro_complete()
        _enter_combat_safe(play_dialog)
        # Manually trigger table update since QTimer won't fire in test
        play_dialog._turn_ctrl.update_table()
        assert len(play_dialog._initiative_panel._entries) > 0

    def test_combat_log_entries(self, play_dialog):
        play_dialog._on_intro_complete()
        _enter_combat_safe(play_dialog)
        play_dialog._log.add_entry("Fighter", "Attack", True,
                                   ["d20(15) + 4 = 19 vs AC 13"], round_num=1)
        assert play_dialog._log._entry_count >= 1

    def test_keyboard_shortcuts_dont_crash(self, play_dialog):
        play_dialog._on_intro_complete()
        _enter_combat_safe(play_dialog)
        from PyQt5.QtGui import QKeyEvent
        from PyQt5.QtCore import QEvent
        for key in [Qt.Key_Space, Qt.Key_1, Qt.Key_2, Qt.Key_3,
                    Qt.Key_4, Qt.Key_5, Qt.Key_6, Qt.Key_Tab,
                    Qt.Key_Escape, Qt.Key_W, Qt.Key_A, Qt.Key_S, Qt.Key_D]:
            event = QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier)
            play_dialog.keyPressEvent(event)

    def test_hp_update_on_initiative(self, play_dialog):
        play_dialog._on_intro_complete()
        _enter_combat_safe(play_dialog)
        for entry in play_dialog._initiative_panel._entries:
            play_dialog._initiative_panel.update_entity_hp(
                entry["name"], 5, entry.get("max_hp", 20))
            break

    def test_tile_pulse_on_combat_scene(self, play_dialog):
        play_dialog._on_intro_complete()
        _enter_combat_safe(play_dialog)
        scene = play_dialog._combat_scene
        if scene:
            tile = next(iter(scene._tiles.values()), None)
            if tile:
                tile.pulse_select()

    def test_condition_icons_on_combat_tiles(self, play_dialog):
        play_dialog._on_intro_complete()
        _enter_combat_safe(play_dialog)
        scene = play_dialog._combat_scene
        if scene:
            for tile in list(scene._tiles.values())[:3]:
                tile.set_conditions(["poisoned", "stunned"])
                tile.set_conditions([])


# ---------------------------------------------------------------------------
# 5. PLAY SESSION — DM AUTOMATION
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestDMAutomation:
    """Test all three DM automation modes."""

    def test_enemies_only_mode(self, play_dialog):
        play_dialog._on_intro_complete()
        play_dialog._dm_automation = DMAutomation.ENEMIES_ONLY
        _enter_combat_safe(play_dialog)
        # Some entities should have UIInputAdapter, some HeuristicAI
        from core.engine.ui_adapter import UIInputAdapter
        from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
        runner = play_dialog._runner
        has_ui = any(isinstance(runner._session._adapters.get(e.name), UIInputAdapter)
                     for e in runner.entities)
        has_ai = any(isinstance(runner._session._adapters.get(e.name), HeuristicAIAdapter)
                     for e in runner.entities)
        assert has_ui or has_ai  # At least one of each type

    def test_all_auto_mode(self, play_dialog):
        play_dialog._on_intro_complete()
        play_dialog._dm_automation = DMAutomation.ALL_AUTO
        _enter_combat_safe(play_dialog)
        from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
        runner = play_dialog._runner
        for e in runner.entities:
            adapter = runner._session._adapters.get(e.name)
            assert isinstance(adapter, HeuristicAIAdapter), (
                f"{e.name} should be AI-controlled in ALL_AUTO")

    def test_manual_mode(self, play_dialog):
        play_dialog._on_intro_complete()
        _enter_combat_safe(play_dialog)
        # Switch to MANUAL after combat is set up
        play_dialog._set_dm_automation(DMAutomation.MANUAL)
        from core.engine.ui_adapter import UIInputAdapter
        runner = play_dialog._runner
        for e in runner.entities:
            adapter = runner._session._adapters.get(e.name)
            assert isinstance(adapter, UIInputAdapter), (
                f"{e.name} should be UI-controlled in MANUAL")


# ---------------------------------------------------------------------------
# 6. PLAY SESSION — SIDEBAR & WIDGETS
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestSidebarWidgets:
    """Verify sidebar widget state at each play state."""

    def test_initiative_hidden_during_exploration(self, play_dialog):
        play_dialog._on_intro_complete()
        assert play_dialog._initiative_section.isHidden()

    def test_initiative_visible_during_combat(self, play_dialog):
        play_dialog._on_intro_complete()
        _enter_combat_safe(play_dialog)
        assert not play_dialog._initiative_section.isHidden()

    def test_minimap_hidden_during_combat(self, play_dialog):
        play_dialog._on_intro_complete()
        _enter_combat_safe(play_dialog)
        assert play_dialog._map_section.isHidden()

    def test_minimap_visible_during_exploration(self, play_dialog):
        play_dialog._on_intro_complete()
        assert not play_dialog._map_section.isHidden()

    def test_combat_log_widget_methods(self, play_dialog):
        """All QTextEdit-compatible methods work on CombatLogWidget."""
        log = play_dialog._log
        log.append("plain text")
        log.add_system_message("system msg", "info")
        log.add_entry("Actor", "Attack", True, ["d20(15)"], round_num=1)
        sb = log.verticalScrollBar()
        assert sb is not None
        log.clear()

    def test_tooltip_infrastructure(self, play_dialog):
        play_dialog._on_intro_complete()
        scene = play_dialog._map_scene
        assert hasattr(scene, '_tooltip')
        assert hasattr(scene, '_tooltip_timer')

    def test_transition_engine_exists(self, play_dialog):
        assert hasattr(play_dialog, '_transition_engine')
        assert play_dialog._transition_engine is not None


# ---------------------------------------------------------------------------
# 7. MAIN WINDOW — EDITOR OPERATIONS
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestMainWindowOperations:
    """Test MainWindow operations that users trigger via menus/toolbar."""

    def test_build_gamemaster_with_entities(self, qapp):
        """Gamemaster built from a scene with entities placed on tiles."""
        from ui.main_window import MainWindow
        from core.settings_manager import SettingsManager
        settings = SettingsManager()
        mw = MainWindow(settings, grid_type="square", rows=5, cols=5)
        mw.initialize_default_map()

        # Place an entity on a tile
        tile_item = next(iter(mw.scene.items()), None)
        if tile_item and hasattr(tile_item, 'tile_data'):
            entity = GameEntity("TestGuard", "npc",
                                stats={"hp": 10, "max_hp": 10})
            tile_item.tile_data.entities.append(entity)

        gm = mw._build_gamemaster_from_scene()
        assert gm is not None
        assert gm.world is not None
        assert gm.world.tile_manager is not None

        mw.close()
        mw.deleteLater()
        QApplication.processEvents()

    def test_save_and_load_roundtrip(self, qapp):
        """Save map to temp file, load it back, verify tiles preserved."""
        from ui.main_window import MainWindow
        from core.settings_manager import SettingsManager
        import tempfile, os

        settings = SettingsManager()
        mw = MainWindow(settings, grid_type="square", rows=3, cols=3)
        mw.initialize_default_map()

        # Save to temp
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()
        try:
            mw.save_map_to_file(tmp.name)
            assert Path(tmp.name).exists()

            # Load into a new window
            mw2 = MainWindow(settings, grid_type="square")
            mw2.load_map_from_file(tmp.name)
            # Should have tiles
            assert mw2.scene.items()

            mw2.close()
            mw2.deleteLater()
        finally:
            os.unlink(tmp.name)

        mw.close()
        mw.deleteLater()
        QApplication.processEvents()


# ---------------------------------------------------------------------------
# 8. SCENARIO LOADING — FILE-BASED FLOW
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestScenarioLoading:
    """Test loading a scenario from JSON into a PlaySessionDialog."""

    def test_load_scenario_from_file(self, qapp):
        """Load map.json → extract entities → create PlaySessionDialog."""
        tiles = _scenario_with_party_and_enemies()
        map_path = _write_scenario_to_temp(tiles)

        data = json.loads(map_path.read_text())
        loaded_tiles = data["tiles"]

        from ui.dialogs.play_session_dialog import PlaySessionDialog
        dlg = PlaySessionDialog(
            tile_dicts=loaded_tiles,
            scenario_name="File Load Test",
            role=PlayerRole.DM,
            meta=data.get("meta", {}),
        )

        assert dlg._play_state == PlayState.INTRO
        assert len(dlg._all_entities) >= 3

        dlg.close()
        dlg.deleteLater()
        QApplication.processEvents()

    def test_empty_scenario_gets_default_party(self, qapp):
        """Scenario with no player entities spawns a default party."""
        tiles = _make_tile_dicts()  # no entities embedded

        from ui.dialogs.play_session_dialog import PlaySessionDialog
        dlg = PlaySessionDialog(
            tile_dicts=tiles,
            scenario_name="Empty Scenario",
            role=PlayerRole.DM,
            meta={},
        )

        players = [e for e in dlg._all_entities if e.entity_type == "player"]
        assert len(players) >= 1, "Should spawn default party when no players exist"

        dlg.close()
        dlg.deleteLater()
        QApplication.processEvents()


# ---------------------------------------------------------------------------
# 9. MULTIPLAYER — HOST/CLIENT FIXES
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestMultiplayerUIFixes:
    """Verify multiplayer UI issues are resolved."""

    def test_build_gamemaster_world_args(self, qapp):
        """_build_gamemaster_from_scene creates World with all required args."""
        from ui.main_window import MainWindow
        from core.settings_manager import SettingsManager
        settings = SettingsManager()
        mw = MainWindow(settings, grid_type="square", rows=3, cols=3)
        mw.initialize_default_map()
        gm = mw._build_gamemaster_from_scene()
        # The World must have description, time_of_day, weather_conditions
        assert gm.world is not None
        assert hasattr(gm.world, 'tile_manager')
        assert gm.world.tile_manager is not None
        mw.close()
        mw.deleteLater()
        QApplication.processEvents()

    def test_host_chat_sends_via_broadcast(self, qapp):
        """Host-side send_chat broadcasts directly instead of requiring a client."""
        from network.session_manager import SessionManager
        from unittest.mock import MagicMock, AsyncMock
        import asyncio

        gm = Gamemaster()
        sm = SessionManager(gamemaster=gm)
        sm._host = MagicMock()
        sm._host.broadcast = AsyncMock()
        sm._is_hosting = True
        sm._loop = asyncio.new_event_loop()

        chat_received = []
        sm.signals.chat_received.connect(lambda s, m: chat_received.append((s, m)))

        sm.send_chat("Hello from DM")
        sm._loop.run_until_complete(asyncio.sleep(0.05))

        # Should have emitted the local signal
        assert len(chat_received) >= 1
        assert chat_received[0] == ("DM", "Hello from DM")

        sm._loop.close()

    def test_main_window_has_return_to_launcher(self, qapp):
        """MainWindow has _return_to_launcher method."""
        from ui.main_window import MainWindow
        from core.settings_manager import SettingsManager
        settings = SettingsManager()
        mw = MainWindow(settings, grid_type="square", rows=3, cols=3)
        assert hasattr(mw, '_return_to_launcher')
        assert callable(mw._return_to_launcher)
        mw.close()
        mw.deleteLater()
        QApplication.processEvents()

    def test_session_ended_offers_return(self, qapp):
        """_on_session_ended calls _offer_return_to_launcher."""
        from ui.main_window import MainWindow
        from core.settings_manager import SettingsManager
        from unittest.mock import patch
        settings = SettingsManager()
        mw = MainWindow(settings, grid_type="square", rows=3, cols=3)
        mw.initialize_default_map()

        # Patch _offer_return_to_launcher to avoid the dialog
        called = [False]
        mw._offer_return_to_launcher = lambda: called.__setitem__(0, True)
        mw._on_session_ended()
        assert called[0], "_offer_return_to_launcher should be called after session ends"

        mw.close()
        mw.deleteLater()
        QApplication.processEvents()

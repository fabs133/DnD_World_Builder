"""Integration tests: verify all registered transitions are wired.

These tests construct a real PlaySessionDialog and check that the
TransitionEngine.execute() method is called with the correct transition
IDs at each state change.  The engine is patched to fire on_complete
immediately so the tests don't depend on animation timing.

Run with: ``pytest -m slow``
"""

from __future__ import annotations

import pytest
from PyQt5.QtWidgets import QApplication

from core.engine.play_state import PlayState, PlayerRole, DMAutomation
from models.entities.game_entity import GameEntity


# ---------------------------------------------------------------------------
# Helpers (duplicated from test_play_session_flow.py for independence)
# ---------------------------------------------------------------------------

def _make_tile_dicts(width=8, height=8, terrain="GRASS"):
    tiles = []
    for r in range(height):
        for c in range(width):
            tags = ["START_ZONE"] if (r, c) == (7, 0) else []
            tiles.append({
                "tile_id": f"t_{r}_{c}",
                "position": [r, c],
                "terrain": terrain,
                "tags": tags,
                "elevation": 0,
                "entities": [],
            })
    return tiles


def _scenario_with_entities():
    tiles = _make_tile_dicts()
    player = {
        "name": "TestHero", "entity_type": "player",
        "stats": {"hp": 30, "max_hp": 30, "armor_class": 15,
                  "speed": 30, "Dexterity": 14},
        "inventory": [], "triggers": [],
    }
    enemy = {
        "name": "Goblin Scout", "entity_type": "enemy",
        "stats": {"hp": 7, "max_hp": 7, "armor_class": 13,
                  "speed": 30, "Dexterity": 14, "Strength": 8},
        "inventory": [], "triggers": [],
    }
    for td in tiles:
        pos = tuple(td["position"])
        if pos == (7, 0):
            td["entities"] = [player]
        elif pos == (7, 1):
            td["entities"] = [enemy]
    return tiles


def _patch_transition_engine(dialog):
    """Patch the dialog's TransitionEngine to record calls and fire immediately."""
    calls = []

    def _fake_execute(transition_id, outgoing=None, incoming=None, on_complete=None):
        calls.append(transition_id)
        # Show/hide widgets like the real engine would
        if outgoing:
            outgoing.hide()
        if incoming:
            incoming.show()
        if on_complete:
            on_complete()

    dialog._transition_engine.execute = _fake_execute
    return calls


def _enter_combat_safe(dialog):
    dialog._dm_automation = DMAutomation.ALL_AUTO
    dialog._enter_combat()
    dialog._is_running = False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def scenario_tiles():
    return _scenario_with_entities()


@pytest.fixture
def dialog(qapp, scenario_tiles):
    from ui.dialogs.play_session_dialog import PlaySessionDialog
    dlg = PlaySessionDialog(
        tile_dicts=scenario_tiles,
        scenario_name="Transition Test",
        role=PlayerRole.DM,
        meta={"description": "Transition wiring test"},
    )
    yield dlg
    dlg._is_running = False
    dlg.close()
    dlg.deleteLater()
    QApplication.processEvents()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestPlaySessionTransitionWiring:
    """Verify play-session transitions fire through TransitionEngine."""

    def test_has_transition_engine(self, dialog):
        assert hasattr(dialog, '_transition_engine')
        assert dialog._transition_engine is not None

    def test_exploration_to_combat(self, dialog):
        """_enter_combat fires exploration_to_combat."""
        calls = _patch_transition_engine(dialog)
        dialog._on_intro_complete()
        _enter_combat_safe(dialog)
        assert "exploration_to_combat" in calls

    def test_combat_to_exploration_victory(self, dialog):
        """Victory fires combat_to_exploration_victory."""
        calls = _patch_transition_engine(dialog)
        dialog._on_intro_complete()
        dialog._run_transition("combat_to_exploration_victory")
        assert "combat_to_exploration_victory" in calls

    def test_combat_to_exploration_defeat(self, dialog):
        """Defeat fires combat_to_exploration_defeat."""
        calls = _patch_transition_engine(dialog)
        dialog._run_transition("combat_to_exploration_defeat")
        assert "combat_to_exploration_defeat" in calls

    def test_tile_detail_to_map(self, dialog):
        """_show_full_map fires tile_detail_to_map."""
        calls = _patch_transition_engine(dialog)
        dialog._on_intro_complete()
        dialog._view_stack.setCurrentIndex(1)  # on zone detail
        dialog._show_full_map()
        assert "tile_detail_to_map" in calls

    def test_map_to_tile_detail(self, dialog):
        """Loading tile from full map fires map_to_tile_detail."""
        calls = _patch_transition_engine(dialog)
        dialog._on_intro_complete()
        dialog._view_stack.setCurrentIndex(2)  # on full map
        dialog._load_tile_at(dialog._start_position)
        assert "map_to_tile_detail" in calls

    def test_return_to_detail_from_full_map(self, dialog):
        """_return_to_detail fires map_to_tile_detail when on full map."""
        calls = _patch_transition_engine(dialog)
        dialog._on_intro_complete()
        dialog._view_stack.setCurrentIndex(2)  # on full map
        dialog._return_to_detail()
        assert "map_to_tile_detail" in calls

    def test_no_transition_when_already_on_detail(self, dialog):
        """_return_to_detail does NOT fire transition when already on detail."""
        calls = _patch_transition_engine(dialog)
        dialog._on_intro_complete()
        dialog._view_stack.setCurrentIndex(1)  # already on zone detail
        dialog._return_to_detail()
        assert "map_to_tile_detail" not in calls

    def test_no_transition_when_loading_tile_on_detail(self, dialog):
        """_load_tile_at does NOT fire transition when already on zone detail."""
        calls = _patch_transition_engine(dialog)
        dialog._on_intro_complete()
        dialog._view_stack.setCurrentIndex(1)  # on zone detail
        dialog._load_tile_at(dialog._start_position)
        assert "map_to_tile_detail" not in calls


@pytest.mark.slow
class TestCombatSoundTransitions:
    """Verify combat lifecycle sounds are wired."""

    def test_initiative_sound_on_combat_enter(self, dialog):
        """Initiative sound plays after combat transition completes."""
        from unittest.mock import patch, MagicMock
        _patch_transition_engine(dialog)  # instant transitions
        dialog._on_intro_complete()

        with patch('core.audio.ui_sound_manager.UISoundManager.instance') as mock_inst:
            mock_snd = MagicMock()
            mock_inst.return_value = mock_snd
            _enter_combat_safe(dialog)
            initiative_calls = [
                c for c in mock_snd.play_shared.call_args_list
                if c[0][0] == "initiative"
            ]
            assert len(initiative_calls) >= 1, (
                f"Expected initiative sound, got: {mock_snd.play_shared.call_args_list}"
            )

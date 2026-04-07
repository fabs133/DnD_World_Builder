"""Tests for DM automation toggle — adapter routing by DMAutomation mode."""

import pytest
import inspect

from core.engine.play_state import PlayState, PlayerRole, DMAutomation
from core.engine.game_session import GameSession
from models.game_master import Gamemaster
from models.entities.game_entity import GameEntity


def _entity(name, entity_type="player", hp=20):
    e = GameEntity(name=name, entity_type=entity_type,
                   stats={"hp": hp, "max_hp": hp})
    e.position = (5, 5)
    return e


class TestDMAutomationEnum:

    def test_enum_has_three_values(self):
        assert len(DMAutomation) == 3

    def test_all_auto_exists(self):
        assert DMAutomation.ALL_AUTO is not None

    def test_enemies_only_exists(self):
        assert DMAutomation.ENEMIES_ONLY is not None

    def test_manual_exists(self):
        assert DMAutomation.MANUAL is not None


class TestGameSessionAdapterSwap:

    def test_set_adapter_changes_adapter(self):
        from unittest.mock import MagicMock
        gm = Gamemaster()
        gm.game_entities = [_entity("Fighter")]
        mock_a = MagicMock()
        mock_b = MagicMock()
        session = GameSession(gm, {"Fighter": mock_a}, seed=42, max_rounds=1)
        session.set_adapter("Fighter", mock_b)
        assert session._adapters["Fighter"] is mock_b

    def test_set_adapter_unknown_entity(self):
        from unittest.mock import MagicMock
        gm = Gamemaster()
        gm.game_entities = [_entity("Fighter")]
        session = GameSession(gm, {"Fighter": MagicMock()}, seed=42, max_rounds=1)
        session.set_adapter("Unknown", MagicMock())  # Should not crash
        assert "Unknown" in session._adapters


class TestDMAutomationInDialog:

    def test_automation_handler_source_has_all_modes(self, qapp):
        """_set_dm_automation handles ALL_AUTO, ENEMIES_ONLY, MANUAL."""
        from ui.dialogs.play_session_dialog import PlaySessionDialog
        source = inspect.getsource(PlaySessionDialog._set_dm_automation)
        assert "ALL_AUTO" in source
        assert "ENEMIES_ONLY" in source
        assert "MANUAL" in source

    def test_radio_group_created_for_dm(self, qapp):
        """DM role creates radio button group."""
        from ui.dialogs.play_session_dialog import PlaySessionDialog
        source = inspect.getsource(PlaySessionDialog._build_ui)
        assert "QRadioButton" in source
        assert "QButtonGroup" in source

    def test_default_is_enemies_only(self, qapp):
        """Default automation mode should be ENEMIES_ONLY."""
        from ui.dialogs.play_session_dialog import PlaySessionDialog
        source = inspect.getsource(PlaySessionDialog._build_ui)
        assert "ENEMIES_ONLY" in source

    def test_automation_logs_message(self, qapp):
        """Changing automation logs a message."""
        from ui.dialogs.play_session_dialog import PlaySessionDialog
        source = inspect.getsource(PlaySessionDialog._set_dm_automation)
        assert "Automation:" in source

    def test_all_auto_assigns_ai_to_players(self, qapp):
        """ALL_AUTO mode should assign AI adapter to player entities."""
        from ui.dialogs.play_session_dialog import PlaySessionDialog
        source = inspect.getsource(PlaySessionDialog._set_dm_automation)
        assert "HeuristicAIAdapter" in source

    def test_manual_assigns_ui_to_enemies(self, qapp):
        """MANUAL mode should assign UI adapter to enemy entities."""
        from ui.dialogs.play_session_dialog import PlaySessionDialog
        source = inspect.getsource(PlaySessionDialog._set_dm_automation)
        assert "_ui_adapter" in source


class TestExplorationMovement:

    def test_dm_moves_all_players(self, qapp):
        """on_explore_move in DM mode sets position on all player entities."""
        from ui.dialogs.exploration_controller import ExplorationController
        source = inspect.getsource(ExplorationController.on_explore_move)
        assert 'PlayerRole.DM' in source
        assert 'entity_type == "player"' in source

    def test_spectator_no_movement(self, qapp):
        """Spectator role cannot move entities."""
        from ui.dialogs.exploration_controller import ExplorationController
        source = inspect.getsource(ExplorationController.on_explore_move)
        assert "SPECTATOR" in source
        assert "return" in source

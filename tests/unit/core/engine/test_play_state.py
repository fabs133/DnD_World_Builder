"""Tests for PlayState and PlayerRole enums."""

from core.engine.play_state import PlayState, PlayerRole


class TestPlayState:
    def test_all_states_exist(self):
        assert PlayState.SETUP
        assert PlayState.INTRO
        assert PlayState.EXPLORATION
        assert PlayState.COMBAT
        assert PlayState.ENDED

    def test_has_5_members(self):
        assert len(PlayState) == 5


class TestPlayerRole:
    def test_all_roles_exist(self):
        assert PlayerRole.PLAYER
        assert PlayerRole.DM
        assert PlayerRole.SPECTATOR

    def test_values(self):
        assert PlayerRole.PLAYER.value == "player"
        assert PlayerRole.DM.value == "dm"
        assert PlayerRole.SPECTATOR.value == "spectator"

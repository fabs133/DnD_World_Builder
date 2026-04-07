"""Tests for dynamic context-aware menu system."""

import pytest
from ui.main_window import AppViewState


class TestAppViewState:

    def test_enum_values(self):
        assert AppViewState.MAP_EDITOR.value == "map_editor"
        assert AppViewState.ZONE_VIEW.value == "zone_view"
        assert AppViewState.COMBAT.value == "combat"

    def test_all_states_exist(self):
        states = list(AppViewState)
        assert len(states) == 3

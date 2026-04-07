"""Tests for FogOfWarState."""

from core.engine.fog_state import FogOfWarState


class TestFogOfWarState:

    def test_initially_all_hidden(self):
        fog = FogOfWarState()
        assert fog.get_tile_state((0, 0)) == "hidden"
        assert fog.get_tile_state((5, 5)) == "hidden"

    def test_update_marks_visible(self):
        fog = FogOfWarState()
        fog.update({(0, 0), (1, 0), (0, 1)})
        assert fog.get_tile_state((0, 0)) == "visible"
        assert fog.get_tile_state((1, 0)) == "visible"

    def test_update_marks_others_hidden(self):
        fog = FogOfWarState()
        fog.update({(0, 0)})
        assert fog.get_tile_state((5, 5)) == "hidden"

    def test_previously_visible_becomes_revealed(self):
        fog = FogOfWarState()
        fog.update({(0, 0), (1, 0)})
        fog.update({(1, 0)})  # (0,0) no longer visible
        assert fog.get_tile_state((0, 0)) == "revealed"
        assert fog.get_tile_state((1, 0)) == "visible"

    def test_revealed_persists_across_updates(self):
        fog = FogOfWarState()
        fog.update({(0, 0)})
        fog.update({(1, 0)})
        fog.update({(2, 0)})
        # All previously seen tiles should be revealed
        assert fog.get_tile_state((0, 0)) == "revealed"
        assert fog.get_tile_state((1, 0)) == "revealed"
        assert fog.get_tile_state((2, 0)) == "visible"

    def test_empty_update_makes_all_revealed(self):
        fog = FogOfWarState()
        fog.update({(0, 0), (1, 1)})
        fog.update(set())
        assert fog.get_tile_state((0, 0)) == "revealed"
        assert fog.get_tile_state((1, 1)) == "revealed"

    def test_revealed_set_grows(self):
        fog = FogOfWarState()
        fog.update({(0, 0)})
        fog.update({(1, 1)})
        assert (0, 0) in fog.revealed
        assert (1, 1) in fog.revealed

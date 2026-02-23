"""Tests for TileEditCommand undo/redo logic."""

import pytest
from unittest.mock import MagicMock

from models.tiles.tile_data import TileData, TerrainType, TileTag
from ui.dialogs.tile_edit.tile_edit_command import TileEditCommand


@pytest.fixture
def tile():
    return TileData(
        tile_id="tile_1",
        position=(2, 3),
        terrain=TerrainType.GRASS,
        tags=[TileTag.START_ZONE],
        user_label="Start",
        note="Starting point",
        overlay_color="#00FF00",
    )


@pytest.fixture
def states(tile):
    old_state = tile.to_dict()
    new_state = tile.to_dict()
    new_state["terrain"] = "WALL"
    new_state["tags"] = ["BLOCKS_MOVEMENT"]
    new_state["user_label"] = "Blocked"
    new_state["note"] = "A wall"
    new_state["overlay_color"] = "#FF0000"
    return old_state, new_state


class TestTileEditCommand:

    def test_redo_applies_new_state(self, qapp, tile, states):
        old_state, new_state = states
        cmd = TileEditCommand(tile, old_state, new_state)
        cmd.redo()
        assert tile.terrain == TerrainType.WALL
        assert TileTag.BLOCKS_MOVEMENT in tile.tags
        assert tile.user_label == "Blocked"

    def test_undo_restores_old_state(self, qapp, tile, states):
        old_state, new_state = states
        cmd = TileEditCommand(tile, old_state, new_state)
        cmd.redo()
        cmd.undo()
        assert tile.terrain == TerrainType.GRASS
        assert TileTag.START_ZONE in tile.tags
        assert tile.user_label == "Start"

    def test_redo_undo_roundtrip(self, qapp, tile, states):
        old_state, new_state = states
        cmd = TileEditCommand(tile, old_state, new_state)
        cmd.redo()
        cmd.undo()
        cmd.redo()
        assert tile.terrain == TerrainType.WALL
        assert tile.note == "A wall"

    def test_tile_item_updated_on_redo(self, qapp, tile, states):
        old_state, new_state = states
        fake_item = MagicMock()
        cmd = TileEditCommand(tile, old_state, new_state, tile_item=fake_item)
        cmd.redo()
        fake_item.set_overlay_color.assert_called_once_with("#FF0000")

    def test_tile_item_updated_on_undo(self, qapp, tile, states):
        old_state, new_state = states
        fake_item = MagicMock()
        cmd = TileEditCommand(tile, old_state, new_state, tile_item=fake_item)
        cmd.redo()
        fake_item.reset_mock()
        cmd.undo()
        fake_item.set_overlay_color.assert_called_once_with("#00FF00")

    def test_command_text_includes_tile_id(self, qapp, tile, states):
        old_state, new_state = states
        cmd = TileEditCommand(tile, old_state, new_state)
        assert "tile_1" in cmd.text()

    def test_no_tile_item_does_not_crash(self, qapp, tile, states):
        old_state, new_state = states
        cmd = TileEditCommand(tile, old_state, new_state, tile_item=None)
        cmd.redo()
        cmd.undo()
        # No error raised

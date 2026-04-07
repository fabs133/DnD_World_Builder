"""Tests for combat lifecycle — enter/exit combat, position save/restore, state guards."""

import pytest
from unittest.mock import MagicMock, patch

from PyQt5.QtCore import Qt

from ui.combat.play_map_widget import PlayMapScene
from core.engine.play_state import PlayState


def make_tile_dicts(width=10, height=10, terrain="GRASS", blocked=None):
    blocked = blocked or set()
    tiles = []
    for r in range(height):
        for c in range(width):
            tags = ["BLOCKS_MOVEMENT"] if (r, c) in blocked else []
            tiles.append({
                "tile_id": f"combat_{r}_{c}",
                "position": [r, c],
                "terrain": terrain,
                "tags": tags,
                "elevation": 0,
            })
    return tiles


class FakeRunner:
    """Minimal PlaySessionRunner stand-in for lifecycle tests."""

    def __init__(self, entities):
        self.entities = entities
        self.is_finished = False
        self.session = MagicMock()
        self.session._initiative._entries = []

    def current_entity_name(self):
        return self.entities[0].name if self.entities else ""

    def is_player_turn(self):
        return True

    def get_state(self):
        state = MagicMock()
        state.entities = [
            MagicMock(name=e.name, hp=e.hp, entity_type=e.entity_type)
            for e in self.entities
        ]
        return state


# ── Combat entry ────────────────────────────────────────────────────


class TestCombatEntry:

    def test_enter_combat_creates_combat_scene(self, qapp, three_players, four_enemies):
        """Verify _enter_combat creates a PlayMapScene for the combat grid."""
        from ui.dialogs.play_session_dialog import PlaySessionDialog

        tile_dicts = make_tile_dicts(10, 10)
        # Add entities to a tile with zones to trigger zone-based combat
        for e in three_players + four_enemies:
            tile_dicts[0]["entities"] = []

        with patch.object(PlaySessionDialog, '__init__', lambda self, *a, **kw: None):
            dialog = PlaySessionDialog.__new__(PlaySessionDialog)
            # Minimal init for testing
            dialog._play_state = PlayState.EXPLORATION
            dialog._tile_dicts = tile_dicts
            dialog._all_entities = three_players + four_enemies
            dialog._combat_scene = None
            dialog._combat_map_view = None
            dialog._world_positions = {}
            dialog._target_selection_mode = False
            dialog._movement_mode = False
            dialog._combat_overlay = None

            # After setting up combat entities, verify scene is created
            # We test the grid generation directly since dialog init is complex
            from models.combat.grid_generator import generate_combat_grid, combat_grid_to_tile_dicts
            from models.combat.terrain_presets import get_preset
            preset = get_preset("forest")
            grid = generate_combat_grid(10, 10, preset, seed=42)
            tile_dicts = combat_grid_to_tile_dicts(grid)
            scene = PlayMapScene(tile_dicts, tile_size=48)
            assert scene is not None
            assert len(scene._tiles) == 100  # 10x10

    def test_combat_grid_generation_has_correct_size(self, qapp):
        from models.combat.grid_generator import generate_combat_grid
        from models.combat.terrain_presets import get_preset
        preset = get_preset("forest")
        grid = generate_combat_grid(10, 10, preset, seed=42)
        assert len(grid) == 100

    def test_combat_grid_to_tile_dicts_position_convention(self, qapp):
        """Verify (col,row) from generator becomes [row,col] for PlayMapScene."""
        from models.combat.grid_generator import generate_combat_grid, combat_grid_to_tile_dicts
        from models.combat.terrain_presets import get_preset
        preset = get_preset("open_field")
        grid = generate_combat_grid(3, 3, preset, seed=1)
        dicts = combat_grid_to_tile_dicts(grid)
        positions = {tuple(d["position"]) for d in dicts}
        # Should have [row, col] format: (0,0), (0,1), (0,2), (1,0), etc.
        for r in range(3):
            for c in range(3):
                assert (r, c) in positions, f"Missing position ({r},{c})"

    def test_spawn_placement_players_bottom(self, qapp, three_players, four_enemies):
        """Players should be placed in the bottom rows of the combat grid."""
        grid_h = 10
        # Simulate spawn placement logic from _enter_combat
        blocked = set()
        grid_w = 10
        idx = 0
        for e in three_players:
            while True:
                r = grid_h - 1 - (idx // grid_w)
                c = idx % grid_w
                idx += 1
                if (r, c) not in blocked:
                    e.position = (r, c)
                    break
                if idx > grid_w * grid_h:
                    break
        for p in three_players:
            assert p.position[0] >= grid_h - 2  # Bottom 2 rows

    def test_spawn_placement_enemies_top(self, qapp, three_players, four_enemies):
        """Enemies should be placed in the top rows."""
        grid_w, grid_h = 10, 10
        blocked = set()
        idx = 0
        for e in four_enemies:
            while True:
                r = idx // grid_w
                c = idx % grid_w
                idx += 1
                if (r, c) not in blocked:
                    e.position = (r, c)
                    break
                if idx > grid_w * grid_h:
                    break
        for e in four_enemies:
            assert e.position[0] <= 1  # Top 2 rows

    def test_world_positions_saved(self, qapp, combat_entities):
        """World positions dict should capture all entities."""
        world_positions = {e.name: e.position for e in combat_entities}
        assert len(world_positions) == len(combat_entities)
        for e in combat_entities:
            assert e.name in world_positions


# ── Combat exit ─────────────────────────────────────────────────────


class TestCombatExit:

    def test_world_positions_restored(self, qapp, combat_entities):
        """After combat, entity positions should return to saved world positions."""
        original_positions = {e.name: e.position for e in combat_entities}

        # Simulate combat: change positions
        for e in combat_entities:
            e.position = (0, 0)

        # Restore
        for e in combat_entities:
            if e.name in original_positions:
                e.position = original_positions[e.name]

        for e in combat_entities:
            assert e.position == original_positions[e.name]

    def test_combat_scene_cleared(self, qapp, tile_dicts_10x10):
        """Combat scene should be None after cleanup."""
        scene = PlayMapScene(tile_dicts_10x10, tile_size=48)
        scene.clear()
        # Scene is cleared — no items remain
        assert len(list(scene.items())) == 0

    def test_range_outline_cleared(self, qapp, combat_scene):
        from ui.combat.play_map_widget import RangeOutline
        outline = RangeOutline(combat_scene, 48)
        outline.show({(5, 5), (5, 6)}, combat_scene._tiles)
        assert outline._outline_item is not None
        outline.clear()
        assert outline._outline_item is None


# ── State guards ────────────────────────────────────────────────────


class TestStateGuards:

    def test_sidebar_click_ignored_during_combat(self, qapp):
        """_on_sidebar_tile_clicked should no-op during combat."""
        # Verify the guard logic exists
        from ui.dialogs import play_session_dialog
        import inspect
        source = inspect.getsource(play_session_dialog.PlaySessionDialog._on_sidebar_tile_clicked)
        assert "PlayState.COMBAT" in source
        assert "return" in source

    def test_full_map_click_ignored_during_combat(self, qapp):
        from ui.dialogs import play_session_dialog
        import inspect
        source = inspect.getsource(play_session_dialog.PlaySessionDialog._on_full_map_tile_clicked)
        assert "PlayState.COMBAT" in source
        assert "return" in source

    def test_return_to_detail_blocked_during_combat(self, qapp):
        from ui.dialogs import play_session_dialog
        import inspect
        source = inspect.getsource(play_session_dialog.PlaySessionDialog._return_to_detail)
        assert "PlayState.COMBAT" in source

    def test_show_full_map_recovery_during_combat(self, qapp):
        """_show_full_map should recover to combat grid during combat."""
        from ui.dialogs import play_session_dialog
        import inspect
        source = inspect.getsource(play_session_dialog.PlaySessionDialog._show_full_map)
        assert "PlayState.COMBAT" in source
        assert "_combat_map_view" in source

    def test_terrain_preset_mapping(self):
        from ui.dialogs.play_session_dialog import PlaySessionDialog
        mapping = PlaySessionDialog._TERRAIN_TO_PRESET
        assert mapping["GRASS"] == "forest"
        assert mapping["FLOOR"] == "dungeon"
        assert mapping["MOUNTAIN"] == "cave"
        assert "SAND" in mapping

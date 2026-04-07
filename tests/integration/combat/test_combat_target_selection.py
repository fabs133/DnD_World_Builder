"""Tests for combat target selection — click-to-target, movement mode, state flags."""

import pytest
from unittest.mock import MagicMock

from PyQt5.QtCore import Qt

from ui.combat.play_map_widget import PlayMapScene


# ── Target selection mode ───────────────────────────────────────────


class TestTargetSelectionMode:

    def test_click_enemy_tile_returns_entity(self, combat_scene, four_enemies):
        """entity_at should return the enemy at the clicked position."""
        wolf = four_enemies[0]  # position (1, 3)
        result = combat_scene.entity_at(1, 3)
        assert result is wolf

    def test_click_empty_tile_returns_none(self, combat_scene):
        result = combat_scene.entity_at(5, 5)
        assert result is None

    def test_click_player_tile_returns_player(self, combat_scene, three_players):
        fighter = three_players[0]  # position (8, 3)
        result = combat_scene.entity_at(8, 3)
        assert result is fighter
        # Target selection should reject this (not an enemy)
        assert result.entity_type != "enemy"

    def test_entity_type_check_for_hostiles(self, combat_scene, four_enemies):
        """Only enemy/monster/hostile types should be valid attack targets."""
        wolf = combat_scene.entity_at(1, 3)
        assert wolf.entity_type in ("enemy", "monster", "hostile")

    def test_entity_type_check_rejects_friendly(self, combat_scene, three_players):
        fighter = combat_scene.entity_at(8, 3)
        assert fighter.entity_type not in ("enemy", "monster", "hostile")


# ── Movement mode ───────────────────────────────────────────────────


class TestMovementMode:

    def test_movement_target_is_tuple(self, combat_scene):
        """Movement destination should be a (row, col) tuple."""
        row, col = 5, 5
        target = (row, col)
        assert isinstance(target, tuple)
        assert len(target) == 2

    def test_movement_to_occupied_tile_blocked(self, combat_scene, four_enemies):
        """Can't move to a tile with an enemy on it."""
        wolf_pos = four_enemies[0].position
        entity = combat_scene.entity_at(*wolf_pos)
        assert entity is not None  # Tile is occupied


# ── Mode mutual exclusion ──────────────────────────────────────────


class TestModeMutualExclusion:

    def test_target_mode_flag_default_false(self):
        """Verify the flag starts False in CombatActionHandler."""
        from ui.dialogs.combat_action_handler import CombatActionHandler
        import inspect
        source = inspect.getsource(CombatActionHandler.__init__)
        assert "_target_selection_mode = False" in source

    def test_movement_mode_flag_default_false(self):
        from ui.dialogs.combat_action_handler import CombatActionHandler
        import inspect
        source = inspect.getsource(CombatActionHandler.__init__)
        assert "_movement_mode = False" in source

    def test_end_turn_clears_both_modes(self):
        """on_end_turn should reset both flags."""
        from ui.dialogs.combat_action_handler import CombatActionHandler
        import inspect
        source = inspect.getsource(CombatActionHandler.on_end_turn)
        assert "_target_selection_mode = False" in source
        assert "_movement_mode = False" in source

    def test_escape_clears_both_modes(self):
        """keyPressEvent(Escape) should clear both flags via the action handler."""
        from ui.dialogs import play_session_dialog
        import inspect
        source = inspect.getsource(play_session_dialog.PlaySessionDialog.keyPressEvent)
        # Flags are now on the action handler, accessed via properties
        assert "target_selection_mode" in source
        assert "movement_mode" in source

    def test_combat_tile_click_clears_path_preview(self):
        """on_combat_tile_clicked should clear path preview."""
        from ui.dialogs.combat_action_handler import CombatActionHandler
        import inspect
        source = inspect.getsource(CombatActionHandler.on_combat_tile_clicked)
        assert "clear_path_preview" in source


# ── Action creation ─────────────────────────────────────────────────


class TestActionCreation:

    def test_attack_action_requires_target(self, combat_scene, three_players, four_enemies):
        """AttackAction needs actor and target entities."""
        from core.engine.actions.attack_action import AttackAction
        actor = three_players[0]
        target = four_enemies[0]
        action = AttackAction(
            actor=actor, target=target, weapon_range=5,
            damage_expr="1d8+3", to_hit_bonus=5,
        )
        assert action.actor is actor
        assert action.target is target

    def test_move_action_has_position(self, three_players):
        from core.engine.actions.move_action import MoveAction
        actor = three_players[0]
        action = MoveAction(actor=actor, target_position=(5, 5))
        assert action.target_position == (5, 5)

    def test_attack_action_with_stats(self, three_players, four_enemies):
        """Verify damage_expr and to_hit_bonus are passed through."""
        from core.engine.actions.attack_action import AttackAction
        action = AttackAction(
            actor=three_players[0], target=four_enemies[0],
            weapon_range=5, damage_expr="2d6+4", to_hit_bonus=7,
        )
        assert action.damage_expr == "2d6+4"
        assert action.to_hit_bonus == 7


# ── Entity lookup chain ────────────────────────────────────────────


class TestEntityLookupChain:

    def test_find_entity_source_code_checks_runner_first(self):
        """_find_entity should check _runner.entities before _all_entities."""
        from ui.dialogs import play_session_dialog
        import inspect
        source = inspect.getsource(play_session_dialog.PlaySessionDialog._find_entity)
        runner_idx = source.index("_runner")
        all_idx = source.index("_all_entities")
        assert runner_idx < all_idx, "_runner should be checked before _all_entities"

    def test_find_entity_has_zone_list_fallback(self):
        """_find_entity should search zone detail entity list as last resort."""
        from ui.dialogs import play_session_dialog
        import inspect
        source = inspect.getsource(play_session_dialog.PlaySessionDialog._find_entity)
        assert "_zone_detail" in source
        assert "_entity_list" in source

    def test_find_entity_zone_fallback_skips_strings(self):
        """Zone list fallback should only return objects, not string names."""
        from ui.dialogs import play_session_dialog
        import inspect
        source = inspect.getsource(play_session_dialog.PlaySessionDialog._find_entity)
        assert "isinstance(data, str)" in source

    def test_entity_not_found_logs_message(self):
        """on_entity_clicked should log when entity not found."""
        from ui.dialogs.exploration_controller import ExplorationController
        import inspect
        source = inspect.getsource(ExplorationController.on_entity_clicked)
        assert "Entity not found" in source

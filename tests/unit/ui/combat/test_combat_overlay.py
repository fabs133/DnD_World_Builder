"""Tests for CombatOverlay."""

import pytest
from unittest.mock import MagicMock, call
from PyQt5.QtGui import QColor

from ui.combat.combat_overlay import CombatOverlay, COLORS
from models.combat.combatant import Combatant, CombatantFaction
from models.combat.combat_instance import CombatInstance, CombatState


class FakeEntity:
    def __init__(self, name="A", hp=10, max_hp=10, speed=30):
        self.name = name
        self.hp = hp
        self.max_hp = max_hp
        self.speed = speed


def _make_instance(combatants, width=5, height=5):
    inst = CombatInstance(
        instance_id="test", template_id="t", template_name="Test",
        grid_width=width, grid_height=height,
        combatants=combatants, state=CombatState.ACTIVE,
    )
    return inst


class TestMovementRange:

    def test_shows_reachable(self, qapp):
        """Movement range with no tile_map just shows origin."""
        scene = MagicMock()
        c = Combatant(entity=FakeEntity("Hero"), faction=CombatantFaction.PLAYER,
                      position=(2, 2), movement_remaining=30)
        inst = _make_instance([c])
        overlay = CombatOverlay(scene, inst, tile_map=None)
        overlay.show_movement_range("Hero")
        # Without tile_map, only origin is reachable — no overlay applied
        # (overlay skips origin)

    def test_clear_calls_scene(self, qapp):
        scene = MagicMock()
        inst = _make_instance([])
        overlay = CombatOverlay(scene, inst)
        overlay.clear_movement_range()
        scene.clear_all_overlays.assert_called_once()


class TestAttackRange:

    def test_melee_adjacent(self, qapp):
        scene = MagicMock()
        c = Combatant(entity=FakeEntity("Hero"), faction=CombatantFaction.PLAYER,
                      position=(2, 2), movement_remaining=30)
        inst = _make_instance([c])
        overlay = CombatOverlay(scene, inst)
        overlay.show_attack_range("Hero", "melee", range_ft=5)
        # Should call apply_overlay_to_tiles with 8 adjacent tiles
        scene.apply_overlay_to_tiles.assert_called_once()
        positions = scene.apply_overlay_to_tiles.call_args[0][0]
        assert len(positions) == 8  # 3x3 grid around (2,2) minus center

    def test_ranged_larger(self, qapp):
        scene = MagicMock()
        c = Combatant(entity=FakeEntity("Archer"), faction=CombatantFaction.PLAYER,
                      position=(5, 5), movement_remaining=30)
        inst = _make_instance([c], width=12, height=12)
        overlay = CombatOverlay(scene, inst)
        overlay.show_attack_range("Archer", "ranged", range_ft=30)
        scene.apply_overlay_to_tiles.assert_called_once()
        positions = scene.apply_overlay_to_tiles.call_args[0][0]
        assert len(positions) > 8


class TestThreatenedSquares:

    def test_enemy_threats(self, qapp):
        scene = MagicMock()
        e = Combatant(entity=FakeEntity("Goblin", hp=5), faction=CombatantFaction.ENEMY,
                      position=(3, 3))
        inst = _make_instance([e])
        overlay = CombatOverlay(scene, inst)
        overlay.show_threatened_squares()
        scene.apply_overlay_to_tiles.assert_called_once()
        positions = scene.apply_overlay_to_tiles.call_args[0][0]
        assert (3, 2) in positions
        assert (2, 3) in positions
        assert (3, 3) not in positions  # enemy's own tile


class TestClearAll:

    def test_clears(self, qapp):
        scene = MagicMock()
        inst = _make_instance([])
        overlay = CombatOverlay(scene, inst)
        overlay.clear_all()
        scene.clear_all_overlays.assert_called_once()


class TestRefreshAll:

    def test_shows_movement_and_threats(self, qapp):
        scene = MagicMock()
        p = Combatant(entity=FakeEntity("Hero"), faction=CombatantFaction.PLAYER,
                      position=(2, 2), movement_remaining=30)
        e = Combatant(entity=FakeEntity("Goblin", hp=5), faction=CombatantFaction.ENEMY,
                      position=(4, 4))
        inst = _make_instance([p, e])
        overlay = CombatOverlay(scene, inst)
        overlay.refresh_all("Hero")
        # Should call clear + apply overlays
        assert scene.clear_all_overlays.called

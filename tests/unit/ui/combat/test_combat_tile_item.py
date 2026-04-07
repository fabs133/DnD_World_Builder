"""Tests for CombatTileItem."""

import pytest
from PyQt5.QtGui import QColor
from ui.combat.combat_tile_item import CombatTileItem
from models.combat.elevation import ELEVATION_PX


class TestCombatTileItem:

    def test_position(self, qapp):
        item = CombatTileItem(col=2, row=3, tile_size=48)
        rect = item.rect()
        assert rect.x() == 96  # 2 * 48
        assert rect.y() == 144  # 3 * 48

    def test_elevation_offset(self, qapp):
        item = CombatTileItem(col=0, row=2, tile_size=48, elevation=2)
        rect = item.rect()
        expected_y = 2 * 48 - (2 * ELEVATION_PX)
        assert rect.y() == expected_y

    def test_zero_elevation_no_offset(self, qapp):
        item = CombatTileItem(col=0, row=2, tile_size=48, elevation=0)
        assert item.rect().y() == 96  # 2 * 48

    def test_negative_elevation(self, qapp):
        item = CombatTileItem(col=0, row=2, tile_size=48, elevation=-1)
        expected_y = 2 * 48 - (-1 * ELEVATION_PX)
        assert item.rect().y() == expected_y

    def test_bounding_rect_includes_side(self, qapp):
        item = CombatTileItem(col=0, row=0, tile_size=48, elevation=3)
        assert item.rect().height() == 48 + 3 * ELEVATION_PX

    def test_set_token(self, qapp):
        item = CombatTileItem(col=0, row=0, tile_size=48)
        item.set_token("Goblin", "enemy")
        assert item._token_name == "Goblin"
        assert item._token_faction == "enemy"

    def test_clear_token(self, qapp):
        item = CombatTileItem(col=0, row=0, tile_size=48)
        item.set_token("Goblin", "enemy")
        item.clear_token()
        assert item._token_name == ""

    def test_set_overlay(self, qapp):
        item = CombatTileItem(col=0, row=0, tile_size=48)
        item.set_overlay(QColor(100, 100, 200), 0.3)
        assert item._overlay_color is not None

    def test_clear_overlay(self, qapp):
        item = CombatTileItem(col=0, row=0, tile_size=48)
        item.set_overlay(QColor(100, 100, 200))
        item.clear_overlay()
        assert item._overlay_color is None

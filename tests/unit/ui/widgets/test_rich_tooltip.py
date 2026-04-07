"""Tests for RichTooltipWidget."""

import pytest
from PyQt5.QtCore import QPoint

from ui.widgets.rich_tooltip import RichTooltipWidget, _health_category


class TestHealthCategory:
    def test_full_hp(self):
        label, _ = _health_category(20, 20)
        assert label == "healthy"

    def test_wounded(self):
        label, _ = _health_category(14, 20)
        assert label == "wounded"

    def test_bloodied(self):
        label, _ = _health_category(8, 20)
        assert label == "bloodied"

    def test_near_death(self):
        label, _ = _health_category(3, 20)
        assert label == "near death"

    def test_unconscious(self):
        label, _ = _health_category(0, 20)
        assert label == "unconscious"

    def test_zero_max_hp(self):
        label, _ = _health_category(0, 0)
        assert label == "dead"


class TestRichTooltipWidget:
    def test_construction(self, qapp):
        tip = RichTooltipWidget()
        assert tip is not None
        assert not tip.isVisible()

    def test_set_tile_content(self, qapp):
        tip = RichTooltipWidget()
        tip.set_tile_content(
            terrain="GRASS",
            elevation=0,
            tags=["START_ZONE"],
            entities=[{"name": "Goblin"}, {"name": "Orc"}],
            role="dm",
        )
        assert "Grass" in tip._title.text()
        body = tip._body.text()
        assert "Goblin" in body
        assert "Orc" in body

    def test_set_tile_content_empty(self, qapp):
        tip = RichTooltipWidget()
        tip.set_tile_content(
            terrain="FLOOR", elevation=0, tags=[], entities=[], role="dm",
        )
        assert "Empty" in tip._body.text()

    def test_set_entity_content_dm(self, qapp):
        tip = RichTooltipWidget()
        tip.set_entity_content(
            name="Goblin", entity_type="enemy",
            hp=7, max_hp=12, ac=13,
            conditions=["poisoned"], role="dm",
        )
        assert "Goblin" in tip._title.text()
        body = tip._body.text()
        assert "7/12" in body
        assert "13" in body
        assert "poisoned" in body
        assert tip._hp_bar is not None

    def test_set_entity_content_player(self, qapp):
        tip = RichTooltipWidget()
        tip.set_entity_content(
            name="Goblin", entity_type="enemy",
            hp=3, max_hp=12, ac=13,
            conditions=[], role="player",
        )
        body = tip._body.text()
        assert "near death" in body
        assert "3/12" not in body
        assert tip._hp_bar is None

    def test_show_and_hide(self, qapp):
        tip = RichTooltipWidget()
        tip.set_tile_content("FLOOR", 0, [], [], "dm")
        tip.show_at(QPoint(100, 100))
        assert tip.isVisible()
        tip.hide_tooltip()
        assert not tip.isVisible()

    def test_hp_bar_cleared_on_tile_switch(self, qapp):
        tip = RichTooltipWidget()
        tip.set_entity_content("G", "enemy", 5, 10, 10, [], "dm")
        assert tip._hp_bar is not None
        tip.set_tile_content("FLOOR", 0, [], [], "dm")
        assert tip._hp_bar is None

"""Tests for SpellSelectorDialog."""

import pytest
from PyQt5.QtCore import Qt
from ui.combat.spell_selector_dialog import SpellSelectorDialog


@pytest.fixture
def spells():
    return [
        {"name": "Fire Bolt", "level": 0, "school": "Evocation",
         "casting_time": "1 action", "range": "120 ft", "desc": "A ranged spell attack."},
        {"name": "Shield", "level": 1, "school": "Abjuration",
         "casting_time": "1 reaction", "range": "Self", "desc": "An invisible barrier."},
        {"name": "Magic Missile", "level": 1, "school": "Evocation",
         "casting_time": "1 action", "range": "120 ft", "desc": "Three darts of force."},
        {"name": "Fireball", "level": 3, "school": "Evocation",
         "casting_time": "1 action", "range": "150 ft", "desc": "A massive explosion."},
    ]


@pytest.fixture
def slots():
    return {
        1: {"used": 1, "maximum": 3},
        3: {"used": 1, "maximum": 1},  # depleted
    }


class TestSpellSelectorDialog:

    def test_creates_without_error(self, qapp, spells, slots):
        dlg = SpellSelectorDialog(spells, slots)
        assert dlg is not None

    def test_tabs_for_spell_levels(self, qapp, spells, slots):
        dlg = SpellSelectorDialog(spells, slots)
        # Should have tabs for cantrips, 1st, and 3rd
        assert dlg._tabs.count() == 3

    def test_cantrip_tab_not_dimmed(self, qapp, spells, slots):
        dlg = SpellSelectorDialog(spells, slots)
        # Tab 0 is cantrips — should have normal color
        color = dlg._tabs.tabBar().tabTextColor(0)
        assert color != Qt.gray

    def test_depleted_tab_dimmed(self, qapp, spells, slots):
        dlg = SpellSelectorDialog(spells, slots)
        # Find the 3rd-level tab (depleted: 0/1 remaining)
        for i in range(dlg._tabs.count()):
            if "3rd" in dlg._tabs.tabText(i):
                color = dlg._tabs.tabBar().tabTextColor(i)
                assert color == Qt.gray
                break

    def test_cast_disabled_without_selection(self, qapp, spells, slots):
        dlg = SpellSelectorDialog(spells, slots)
        assert not dlg._cast_btn.isEnabled()

    def test_select_cantrip_enables_cast(self, qapp, spells, slots):
        dlg = SpellSelectorDialog(spells, slots)
        # Select the first cantrip card
        cantrip_cards = [c for c in dlg._spell_cards if c.property("spell_level") == 0]
        assert len(cantrip_cards) >= 1
        dlg._select_card(cantrip_cards[0])
        assert dlg._cast_btn.isEnabled()

    def test_spell_selected_signal(self, qapp, spells, slots):
        dlg = SpellSelectorDialog(spells, slots)
        results = []
        dlg.spell_selected.connect(lambda d: results.append(d))

        cantrip_cards = [c for c in dlg._spell_cards if c.property("spell_level") == 0]
        dlg._select_card(cantrip_cards[0])
        dlg._on_cast()

        assert len(results) == 1
        assert results[0]["name"] == "Fire Bolt"

    def test_cancel_closes(self, qapp, spells, slots):
        dlg = SpellSelectorDialog(spells, slots)
        # Cancel should not crash
        dlg.reject()

    def test_empty_spells(self, qapp):
        dlg = SpellSelectorDialog([], {})
        assert dlg._tabs.count() == 0

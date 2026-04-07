"""Tests for PartyStatusStrip."""

import pytest
from PyQt5.QtWidgets import QApplication
from ui.panels.party_status_strip import PartyStatusStrip


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class TestPartyStatusStrip:

    def test_creates_without_error(self, qapp):
        strip = PartyStatusStrip()
        assert strip is not None

    def test_set_party_populates_rows(self, qapp):
        strip = PartyStatusStrip()
        strip.set_party([
            {"name": "Fighter", "hp": 25, "max_hp": 28},
            {"name": "Wizard", "hp": 18, "max_hp": 18},
        ])
        assert len(strip._rows) == 2
        assert "Fighter" in strip._rows
        assert "Wizard" in strip._rows

    def test_hp_bar_shows_correct_values(self, qapp):
        strip = PartyStatusStrip()
        strip.set_party([{"name": "Rogue", "hp": 10, "max_hp": 14}])
        bar = strip._rows["Rogue"]["bar"]
        assert bar.value() == 10
        assert bar.maximum() == 14

    def test_update_entity_hp(self, qapp):
        strip = PartyStatusStrip()
        strip.set_party([{"name": "Cleric", "hp": 24, "max_hp": 24}])
        strip.update_entity_hp("Cleric", 12, 24)
        bar = strip._rows["Cleric"]["bar"]
        assert bar.value() == 12

    def test_update_unknown_entity_no_crash(self, qapp):
        strip = PartyStatusStrip()
        strip.set_party([{"name": "Fighter", "hp": 20, "max_hp": 20}])
        strip.update_entity_hp("Nobody", 5, 10)  # should not crash

    def test_clear(self, qapp):
        strip = PartyStatusStrip()
        strip.set_party([{"name": "Fighter", "hp": 20, "max_hp": 20}])
        strip.clear()
        assert len(strip._rows) == 0

    def test_set_party_replaces_previous(self, qapp):
        strip = PartyStatusStrip()
        strip.set_party([{"name": "A", "hp": 1, "max_hp": 1}])
        strip.set_party([{"name": "B", "hp": 2, "max_hp": 2}])
        assert "A" not in strip._rows
        assert "B" in strip._rows

    def test_entity_selected_signal(self, qapp, qtbot):
        strip = PartyStatusStrip()
        strip.set_party([{"name": "Fighter", "hp": 20, "max_hp": 20}])
        # We can't easily simulate a click on the container, but verify signal exists
        assert hasattr(strip, "entity_selected")

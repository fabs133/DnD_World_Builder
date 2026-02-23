"""Tests for InitiativePanel: population, highlighting, HP updates."""

import pytest

from ui.panels.initiative_panel import InitiativePanel, _InitiativeRow


@pytest.fixture
def entries():
    return [
        {"name": "Rogue", "roll": 18, "hp": 25, "max_hp": 25, "entity_type": "player"},
        {"name": "Goblin", "roll": 14, "hp": 7, "max_hp": 7, "entity_type": "enemy"},
        {"name": "Paladin", "roll": 10, "hp": 40, "max_hp": 40, "entity_type": "player"},
    ]


@pytest.fixture
def panel(qapp, entries):
    p = InitiativePanel()
    p.set_initiative_order(entries)
    return p


class TestInitiativePanelInit:

    def test_default_state(self, qapp):
        p = InitiativePanel()
        assert p._list.count() == 0
        assert "Round: --" in p._round_label.text()

    def test_header_text(self, qapp):
        p = InitiativePanel()
        assert "Initiative" in p._header.text()


class TestSetInitiativeOrder:

    def test_populates_list(self, panel, entries):
        assert panel._list.count() == len(entries)

    def test_entries_stored(self, panel, entries):
        assert len(panel._entries) == 3
        assert panel._entries[0]["name"] == "Rogue"

    def test_row_widgets_created(self, panel):
        for i in range(panel._list.count()):
            widget = panel._list.itemWidget(panel._list.item(i))
            assert isinstance(widget, _InitiativeRow)

    def test_row_displays_entity_name(self, panel):
        widget = panel._list.itemWidget(panel._list.item(0))
        assert widget.entity_name == "Rogue"


class TestSetCurrentTurn:

    def test_updates_round_label(self, panel):
        panel.set_current_turn("Rogue", 3)
        assert "Round: 3" in panel._round_label.text()

    def test_highlights_current_entity(self, panel):
        panel.set_current_turn("Goblin", 1)
        # The Goblin row (index 1) should be active
        widget = panel._list.itemWidget(panel._list.item(1))
        assert "bold" in widget._name_label.styleSheet()

    def test_unhighlights_others(self, panel):
        panel.set_current_turn("Goblin", 1)
        # Rogue row (index 0) should NOT be active
        widget = panel._list.itemWidget(panel._list.item(0))
        assert "bold" not in widget._name_label.styleSheet()

    def test_tracks_current_entity(self, panel):
        panel.set_current_turn("Paladin", 2)
        assert panel._current_entity == "Paladin"


class TestUpdateEntityHP:

    def test_updates_hp_in_entries(self, panel):
        panel.update_entity_hp("Goblin", 3, 7)
        goblin = next(e for e in panel._entries if e["name"] == "Goblin")
        assert goblin["hp"] == 3
        assert goblin["max_hp"] == 7

    def test_rebuilds_list(self, panel):
        panel.update_entity_hp("Rogue", 20, 25)
        assert panel._list.count() == 3


class TestClear:

    def test_clears_all(self, panel):
        panel.clear()
        assert panel._list.count() == 0
        assert panel._entries == []
        assert panel._current_entity is None
        assert "Round: --" in panel._round_label.text()


class TestEntitySelectedSignal:

    def test_signal_emitted_on_row_change(self, panel):
        received = []
        panel.entity_selected.connect(lambda name: received.append(name))
        panel._list.setCurrentRow(1)
        assert received == ["Goblin"]


class TestInitiativeRow:

    def test_displays_name(self, qapp):
        row = _InitiativeRow({"name": "Dragon", "roll": 22})
        assert row.entity_name == "Dragon"

    def test_displays_entity_type(self, qapp):
        row = _InitiativeRow({"name": "Orc", "roll": 15, "entity_type": "enemy"})
        assert "enemy" in row._name_label.text()

    def test_set_active_bold(self, qapp):
        row = _InitiativeRow({"name": "Elf", "roll": 12})
        row.set_active(True)
        assert "bold" in row._name_label.styleSheet()

    def test_set_inactive_clears_style(self, qapp):
        row = _InitiativeRow({"name": "Elf", "roll": 12})
        row.set_active(True)
        row.set_active(False)
        assert "bold" not in row._name_label.styleSheet()

    def test_hp_bar_when_provided(self, qapp):
        from PyQt5.QtWidgets import QProgressBar
        row = _InitiativeRow({"name": "Fighter", "roll": 16, "hp": 30, "max_hp": 50})
        bars = row.findChildren(QProgressBar)
        assert len(bars) == 1
        assert bars[0].value() == 30

    def test_no_hp_bar_when_missing(self, qapp):
        from PyQt5.QtWidgets import QProgressBar
        row = _InitiativeRow({"name": "Ghost", "roll": 10})
        bars = row.findChildren(QProgressBar)
        assert len(bars) == 0

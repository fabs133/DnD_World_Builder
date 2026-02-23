"""Tests for TriggerPanel: load, list, filter, add/delete."""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ui.panels.trigger_panel import TriggerPanel


@pytest.fixture(autouse=True)
def stub_graph_view(monkeypatch):
    """Stub TriggerGraphView to avoid heavy Qt graphics."""
    from PyQt5.QtWidgets import QWidget

    class FakeGraph(QWidget):
        def set_context(self, ctx):
            self._ctx = ctx
        def refresh(self):
            pass

    monkeypatch.setattr("ui.panels.trigger_panel.TriggerGraphView", FakeGraph)


@pytest.fixture
def make_trigger():
    def _make(label):
        return SimpleNamespace(
            label=label,
            event_type="ENTER_TILE",
            condition=MagicMock(__class__=type("AlwaysTrue", (), {})),
            reaction=MagicMock(__class__=type("ApplyDamage", (), {})),
            next_trigger=None,
        )
    return _make


class TestTriggerPanelLoad:

    def test_load_sets_header(self, qapp, make_trigger):
        panel = TriggerPanel()
        ctx = SimpleNamespace(triggers=[])
        panel.load(ctx, "Tile (2,3)")
        assert "Tile (2,3)" in panel.context_label.text()

    def test_load_populates_list(self, qapp, make_trigger):
        panel = TriggerPanel()
        t1 = make_trigger("trap_1")
        t2 = make_trigger("trap_2")
        ctx = SimpleNamespace(triggers=[t1, t2])
        panel.load(ctx, "Test")
        assert panel.trigger_list.count() == 2

    def test_load_empty_shows_empty_label(self, qapp):
        panel = TriggerPanel()
        panel.show()
        ctx = SimpleNamespace(triggers=[])
        panel.load(ctx, "Test")
        # empty_label should not be hidden; trigger_list should be hidden
        assert not panel.empty_label.isHidden()
        assert panel.trigger_list.isHidden()


class TestTriggerPanelFilter:

    def test_filter_hides_non_matching(self, qapp, make_trigger):
        panel = TriggerPanel()
        ctx = SimpleNamespace(triggers=[make_trigger("fire_trap"), make_trigger("ice_wall")])
        panel.load(ctx, "Test")
        panel.filter_input.setText("fire")
        visible = [
            panel.trigger_list.item(i).text()
            for i in range(panel.trigger_list.count())
            if not panel.trigger_list.item(i).isHidden()
        ]
        assert visible == ["fire_trap"]

    def test_clear_filter_shows_all(self, qapp, make_trigger):
        panel = TriggerPanel()
        ctx = SimpleNamespace(triggers=[make_trigger("a"), make_trigger("b")])
        panel.load(ctx, "Test")
        panel.filter_input.setText("a")
        panel.filter_input.setText("")
        hidden = sum(
            1
            for i in range(panel.trigger_list.count())
            if panel.trigger_list.item(i).isHidden()
        )
        assert hidden == 0


class TestTriggerPanelDelete:

    def test_delete_removes_from_context(self, qapp, make_trigger):
        panel = TriggerPanel()
        t1 = make_trigger("trap_1")
        ctx = SimpleNamespace(triggers=[t1])
        panel.load(ctx, "Test")
        # Select and set the trigger in property editor
        panel.property_editor.trigger = t1
        panel._on_delete_trigger()
        assert len(ctx.triggers) == 0
        assert panel.trigger_list.count() == 0


class TestTriggerPanelNew:

    def test_new_clears_selection(self, qapp, make_trigger):
        panel = TriggerPanel()
        ctx = SimpleNamespace(triggers=[make_trigger("trap_1")])
        panel.load(ctx, "Test")
        panel.trigger_list.setCurrentRow(0)
        panel._on_new_trigger()
        # clearSelection() deselects but may not reset currentRow;
        # verify no item is selected
        assert len(panel.trigger_list.selectedItems()) == 0

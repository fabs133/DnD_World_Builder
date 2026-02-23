"""Tests for TriggerListView population and clearing."""

import pytest
from types import SimpleNamespace

from ui.dialogs.trigger_editor.list_view import TriggerListView


@pytest.fixture
def triggers():
    return [
        SimpleNamespace(label="ENTER_TILE:Damage:A1"),
        SimpleNamespace(label="ON_DAMAGE:Alert:B2"),
        SimpleNamespace(label="TURN_START:Sound:C3"),
    ]


class TestTriggerListView:

    def test_empty_context(self, qapp):
        view = TriggerListView()
        view.set_context(SimpleNamespace())
        assert view.list_widget.count() == 0

    def test_populates_from_context(self, qapp, triggers):
        view = TriggerListView()
        ctx = SimpleNamespace(triggers=triggers)
        view.set_context(ctx)
        assert view.list_widget.count() == 3
        labels = [view.list_widget.item(i).text() for i in range(3)]
        assert labels[0] == "ENTER_TILE:Damage:A1"
        assert labels[2] == "TURN_START:Sound:C3"

    def test_set_context_clears_previous(self, qapp, triggers):
        view = TriggerListView()
        view.set_context(SimpleNamespace(triggers=triggers))
        assert view.list_widget.count() == 3
        view.set_context(SimpleNamespace(triggers=[triggers[0]]))
        assert view.list_widget.count() == 1

    def test_no_triggers_attribute(self, qapp):
        view = TriggerListView()
        view.set_context(object())
        assert view.list_widget.count() == 0

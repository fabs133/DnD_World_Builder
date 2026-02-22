import pytest
import PyQt5.QtCore as qc
from PyQt5.QtWidgets import QTabWidget, QPushButton

from ui.dialogs.trigger_editor.editor_dialog import TriggerEditorDialog


# ---------------------------------------------------------------------------
# Minimal stubs
# ---------------------------------------------------------------------------

class _Cond:
    pass


class _React:
    pass


class FakeTrigger:
    def __init__(self, label, next_trigger=None):
        self.label = label
        self.event_type = "ENTER_TILE"
        self.condition = _Cond()
        self.reaction = _React()
        self.next_trigger = next_trigger


class FakeContext:
    def __init__(self, triggers=None):
        self.name = "FakeTile"
        self.triggers = list(triggers or [])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def no_timer(monkeypatch):
    """Disable deferred QTimer.singleShot so graph builds synchronously."""
    monkeypatch.setattr(qc.QTimer, "singleShot", lambda *a, **k: None)


@pytest.fixture
def ctx():
    t1 = FakeTrigger("trigger_A")
    t2 = FakeTrigger("trigger_B", next_trigger="trigger_A")
    return FakeContext([t1, t2])


@pytest.fixture
def dlg(qapp, ctx):
    return TriggerEditorDialog(ctx)


# ---------------------------------------------------------------------------
# Tests — structure
# ---------------------------------------------------------------------------

def test_dialog_has_three_tabs(dlg):
    tabs = dlg.findChild(QTabWidget)
    assert tabs is not None
    labels = [tabs.tabText(i) for i in range(tabs.count())]
    assert labels == ["Graph", "Properties", "Triggers"]


def test_dialog_minimum_size(dlg):
    assert dlg.minimumWidth() >= 900
    assert dlg.minimumHeight() >= 650


def test_dialog_has_save_new_delete_buttons(dlg):
    btns = {b.text() for b in dlg.findChildren(QPushButton)}
    assert "New Trigger" in btns
    assert "Save Trigger" in btns
    assert "Delete Trigger" in btns


# ---------------------------------------------------------------------------
# Tests — _on_new_trigger
# ---------------------------------------------------------------------------

def test_new_trigger_switches_to_properties_tab(dlg):
    dlg.tabs.setCurrentWidget(dlg.graph_view)
    dlg._on_new_trigger()
    assert dlg.tabs.currentWidget() is dlg.property_editor


def test_new_trigger_clears_trigger_selection(dlg, ctx):
    dlg.property_editor.set_trigger(ctx.triggers[0])
    dlg._on_new_trigger()
    assert dlg.property_editor.trigger is None


# ---------------------------------------------------------------------------
# Tests — _on_node_selected
# ---------------------------------------------------------------------------

def test_node_selected_switches_to_properties_tab(dlg, ctx):
    dlg.tabs.setCurrentWidget(dlg.graph_view)
    dlg._on_node_selected(ctx.triggers[0])
    assert dlg.tabs.currentWidget() is dlg.property_editor


def test_node_selected_loads_trigger(dlg, ctx):
    t = ctx.triggers[0]
    dlg._on_node_selected(t)
    # property_editor.trigger is a deepcopy, so compare label
    assert dlg.property_editor.trigger.label == t.label


# ---------------------------------------------------------------------------
# Tests — _on_delete_trigger
# ---------------------------------------------------------------------------

def test_delete_trigger_removes_from_context(dlg, ctx):
    t = ctx.triggers[0]
    dlg.property_editor.set_trigger(t)
    before = len(ctx.triggers)
    dlg._on_delete_trigger()
    assert len(ctx.triggers) == before - 1
    assert not any(tr.label == t.label for tr in ctx.triggers)


def test_delete_noop_when_no_trigger_selected(dlg, ctx):
    dlg.property_editor.trigger = None
    before = len(ctx.triggers)
    dlg._on_delete_trigger()
    assert len(ctx.triggers) == before


# ---------------------------------------------------------------------------
# Tests — legacy compat
# ---------------------------------------------------------------------------

def test_create_new_trigger_alias(dlg):
    """create_new_trigger() should behave identically to _on_new_trigger()."""
    dlg.tabs.setCurrentWidget(dlg.graph_view)
    dlg.create_new_trigger()
    assert dlg.tabs.currentWidget() is dlg.property_editor

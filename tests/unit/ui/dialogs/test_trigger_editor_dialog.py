import pytest
from types import SimpleNamespace

from PyQt5.QtWidgets import QPushButton, QDialog, QWidget, QVBoxLayout
import ui.dialogs.trigger_editor.editor_dialog as te_mod
from ui.dialogs.trigger_editor.editor_dialog import TriggerEditorDialog

# Dummy trigger, minimal fields
class DummyTrigger:
    def __init__(self, event_type, source, reaction, check_and_react):
        self.event_type      = event_type
        self.source          = source
        # a dummy condition function (Dialog only looks at its __class__.__name__)
        self.condition      = lambda data: True
        # reaction can be any callable/object
        self.reaction       = reaction
        self.check_and_react = check_and_react
        self.label          = f"{event_type}"
        self.next_trigger   = None



# Fake registry that holds triggers and exposes get_all_triggers/remove_trigger
class FakeRegistry:
    def __init__(self, triggers):
        self.triggers = list(triggers)
    def get_all_triggers(self):
        return list(self.triggers)
    def remove_trigger(self, trigger):
        self.triggers.remove(trigger)

@pytest.fixture(autouse=True)
def stub_eventbus(monkeypatch):
    calls = []
    import core.gameCreation.event_bus as eb_mod
    # Stub unsubscribe to record calls
    monkeypatch.setattr(
        eb_mod.EventBus,
        "unsubscribe",
        classmethod(lambda cls, ev, cb: calls.append((ev, cb)))
    )
    return calls

@pytest.fixture(autouse=True)
def stub_editor_stack(monkeypatch):
    """
    Replace the real EditorStack (and its child views) with a simple
    widget that puts one Remove button per trigger.
    """
    import ui.dialogs.trigger_editor.editor_stack as es_mod
    import core.gameCreation.event_bus as eb_mod

    class FakeStack(QWidget):
        def __init__(self, registry):
            super().__init__()
            layout = QVBoxLayout(self)
            # For each trigger, create a Remove button wired to both unsubscribe + registry.remove
            for trig in registry.get_all_triggers():
                btn = QPushButton("Remove")
                # when clicked: 1) unsubscribe, 2) remove from registry
                btn.clicked.connect(lambda _, t=trig: (
                    eb_mod.EventBus.unsubscribe(t.event_type, t.check_and_react),
                    registry.remove_trigger(t)
                ))
                layout.addWidget(btn)

    # Patch EditorStack to our FakeStack
    monkeypatch.setattr(es_mod, "TriggerEditorStack", FakeStack)
    # Disable any deferred QTimer.singleShot
    import PyQt5.QtCore as qc
    monkeypatch.setattr(qc.QTimer, "singleShot", lambda *a, **k: None)

@pytest.fixture
def dummy_triggers():
    return [
        DummyTrigger("EVT1", "S1", lambda data: None, lambda data: None),
        DummyTrigger("EVT2", "S2", lambda data: None, lambda data: None),
    ]


@pytest.fixture
def dialog(qapp, dummy_triggers):
    # Build dialog with our fake registry + stubbed exec_
    reg = FakeRegistry(dummy_triggers)
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(QDialog, "exec_", lambda self: None)
    dlg = TriggerEditorDialog(reg)
    monkeypatch.undo()
    return dlg, reg

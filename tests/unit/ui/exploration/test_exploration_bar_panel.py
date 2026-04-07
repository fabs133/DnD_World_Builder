"""Tests for ExplorationBarPanel."""

import pytest
from PyQt5.QtWidgets import QApplication
from ui.exploration.exploration_bar_panel import ExplorationBarPanel


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class TestExplorationBarPanel:

    def test_creates_without_error(self, qapp):
        panel = ExplorationBarPanel()
        assert panel is not None

    def test_has_all_buttons(self, qapp):
        panel = ExplorationBarPanel()
        for key in ("interact", "search", "sneak", "short_rest", "long_rest"):
            assert key in panel._buttons

    def test_action_signal_fires(self, qapp, qtbot):
        panel = ExplorationBarPanel()
        with qtbot.waitSignal(panel.action_selected, timeout=500) as blocker:
            panel._buttons["search"].click()
        assert blocker.args == ["search"]

    def test_rest_signal_fires(self, qapp, qtbot):
        panel = ExplorationBarPanel()
        with qtbot.waitSignal(panel.rest_requested, timeout=500) as blocker:
            panel._buttons["long_rest"].click()
        assert blocker.args == ["long_rest"]

    def test_set_enabled_disables_all(self, qapp):
        panel = ExplorationBarPanel()
        panel.set_enabled(False)
        for btn in panel._buttons.values():
            assert not btn.isEnabled()

    def test_spectator_role_disables(self, qapp):
        panel = ExplorationBarPanel(role="spectator")
        for btn in panel._buttons.values():
            assert not btn.isEnabled()

    def test_set_interact_enabled(self, qapp):
        panel = ExplorationBarPanel()
        panel.set_interact_enabled(False)
        assert not panel._buttons["interact"].isEnabled()
        panel.set_interact_enabled(True)
        assert panel._buttons["interact"].isEnabled()

    def test_set_rest_available(self, qapp):
        panel = ExplorationBarPanel()
        panel.set_rest_available(short=False, long=True)
        assert not panel._buttons["short_rest"].isEnabled()
        assert panel._buttons["long_rest"].isEnabled()

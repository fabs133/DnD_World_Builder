"""Tests for TutorialDialog crash fix."""

import pytest
from unittest.mock import MagicMock
from PyQt5.QtCore import Qt

from ui.dialogs.tutorial_dialog import TutorialDialog


@pytest.fixture
def settings():
    return MagicMock()


class TestTutorialDialog:

    def test_creates_without_crash(self, qapp, settings):
        dlg = TutorialDialog(settings)
        assert dlg is not None

    def test_no_delete_on_close(self, qapp, settings):
        dlg = TutorialDialog(settings)
        assert not dlg.testAttribute(Qt.WA_DeleteOnClose)

    def test_accept_saves_setting_when_checked(self, qapp, settings):
        dlg = TutorialDialog(settings)
        dlg._no_show_cb.setChecked(True)
        dlg.accept()
        settings.set.assert_called_with("show_tutorial", False)

    def test_accept_no_save_when_unchecked(self, qapp, settings):
        dlg = TutorialDialog(settings)
        dlg._no_show_cb.setChecked(False)
        dlg.accept()
        settings.set.assert_not_called()

    def test_has_get_started_button(self, qapp, settings):
        from PyQt5.QtWidgets import QPushButton
        dlg = TutorialDialog(settings)
        buttons = dlg.findChildren(QPushButton)
        labels = [b.text() for b in buttons]
        assert "Get Started" in labels

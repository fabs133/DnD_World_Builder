"""Tests for ColorModeDialog: init, color preview, toggle."""

import pytest
from unittest.mock import MagicMock, patch

from PyQt5.QtWidgets import QDialog
from ui.panels.color_mode_dialog import ColorModeDialog


class TestColorModeDialogInit:

    def test_default_color(self, qapp):
        dlg = ColorModeDialog()
        assert dlg.color == "#CCCCCC"

    def test_custom_initial_color(self, qapp):
        dlg = ColorModeDialog(current_color="#FF0000")
        assert dlg.color == "#FF0000"

    def test_color_mode_default_off(self, qapp):
        dlg = ColorModeDialog()
        assert dlg.color_mode is False

    def test_color_mode_initially_active(self, qapp):
        dlg = ColorModeDialog(color_mode_active=True)
        assert dlg.color_mode is True

    def test_window_title(self, qapp):
        dlg = ColorModeDialog()
        assert dlg.windowTitle() == "Color Mode"


class TestAccept:

    def test_accept_reads_checkbox(self, qapp, monkeypatch):
        dlg = ColorModeDialog()
        dlg._mode_cb.setChecked(True)
        monkeypatch.setattr(QDialog, "accept", lambda self: None)
        dlg.accept()
        assert dlg.color_mode is True

    def test_accept_unchecked(self, qapp, monkeypatch):
        dlg = ColorModeDialog(color_mode_active=True)
        dlg._mode_cb.setChecked(False)
        monkeypatch.setattr(QDialog, "accept", lambda self: None)
        dlg.accept()
        assert dlg.color_mode is False


class TestColorPreview:

    def test_preview_has_background_style(self, qapp):
        dlg = ColorModeDialog(current_color="#00FF00")
        style = dlg._preview.styleSheet()
        assert "#00FF00" in style

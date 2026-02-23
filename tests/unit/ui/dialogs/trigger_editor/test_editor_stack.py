"""Tests for TriggerEditorStack view switching."""

import pytest
from unittest.mock import MagicMock

from PyQt5.QtWidgets import QStackedWidget, QWidget


@pytest.fixture(autouse=True)
def stub_child_views(monkeypatch):
    """Stub heavy child widgets before importing the module."""
    monkeypatch.setattr(
        "ui.dialogs.trigger_editor.editor_stack.TriggerListView",
        lambda: QWidget(),
    )
    monkeypatch.setattr(
        "ui.dialogs.trigger_editor.editor_stack.TriggerPropertyEditor",
        lambda: QWidget(),
    )
    monkeypatch.setattr(
        "ui.dialogs.trigger_editor.editor_stack.TriggerGraphView",
        lambda: QWidget(),
    )


class TestTriggerEditorStack:

    def test_initial_state(self, qapp):
        from ui.dialogs.trigger_editor.editor_stack import TriggerEditorStack
        stack = TriggerEditorStack()
        assert isinstance(stack, QStackedWidget)
        assert stack.count() == 3
        assert stack.context is None

    def test_show_list_view(self, qapp):
        from ui.dialogs.trigger_editor.editor_stack import TriggerEditorStack
        stack = TriggerEditorStack()
        stack.show_list_view()
        assert stack.currentWidget() is stack.list_view

    def test_show_property_view(self, qapp):
        from ui.dialogs.trigger_editor.editor_stack import TriggerEditorStack
        stack = TriggerEditorStack()
        stack.property_editor.set_trigger = MagicMock()
        stack.show_property_view()
        assert stack.currentWidget() is stack.property_editor

    def test_show_graph_view(self, qapp):
        from ui.dialogs.trigger_editor.editor_stack import TriggerEditorStack
        stack = TriggerEditorStack()
        stack.graph_view.refresh = MagicMock()
        stack.show_graph_view()
        assert stack.currentWidget() is stack.graph_view
        stack.graph_view.refresh.assert_called_once()

    def test_set_context(self, qapp):
        from ui.dialogs.trigger_editor.editor_stack import TriggerEditorStack
        stack = TriggerEditorStack()
        stack.list_view.set_context = MagicMock()
        stack.graph_view.set_context = MagicMock()
        stack.property_editor.set_context = MagicMock()

        ctx = MagicMock()
        stack.set_context(ctx)
        assert stack.context is ctx
        stack.list_view.set_context.assert_called_once_with(ctx)
        stack.graph_view.set_context.assert_called_once_with(ctx)
        stack.property_editor.set_context.assert_called_once_with(ctx)

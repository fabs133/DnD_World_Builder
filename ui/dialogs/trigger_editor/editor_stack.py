# trigger_editor/editor_stack.py

from PyQt5.QtWidgets import QStackedWidget
from .list_view import TriggerListView
from .property_editor import TriggerPropertyEditor
from .graph_view import TriggerGraphView

class TriggerEditorStack(QStackedWidget):
    """
    A stacked widget that manages different views for editing triggers.

    This widget allows switching between a list view, a property editor, and a graph view
    for editing triggers associated with a tile or game entity.
    """

    def __init__(self, parent=None):
        """
        Initialize the TriggerEditorStack.

        :param parent: The parent widget, if any.
        :type parent: QWidget or None
        """
        super().__init__(parent)
        self.context = None  # Can be a TileData or GameEntity

        self.list_view = TriggerListView()
        self.property_editor = TriggerPropertyEditor()
        self.graph_view = TriggerGraphView()

        self.addWidget(self.list_view)
        self.addWidget(self.property_editor)
        self.addWidget(self.graph_view)

        # Connect signals later (e.g. list_view.trigger_selected.connect(...))

    def set_context(self, obj):
        """
        Set the currently selected tile or entity whose triggers are being edited.

        :param obj: The context object (TileData or GameEntity).
        :type obj: object
        """
        self.context = obj
        self.list_view.set_context(obj)
        self.graph_view.set_context(obj)
        self.property_editor.set_context(obj)

    def show_list_view(self):
        """
        Show the trigger list view.
        """
        self.setCurrentWidget(self.list_view)

    def show_property_view(self, trigger=None):
        """
        Show the trigger property editor view.

        :param trigger: The trigger to edit, or None to clear selection.
        :type trigger: object or None
        """
        self.property_editor.set_trigger(trigger)
        self.setCurrentWidget(self.property_editor)

    def show_graph_view(self):
        """
        Show the trigger graph view.
        """
        self.graph_view.refresh()
        self.setCurrentWidget(self.graph_view)

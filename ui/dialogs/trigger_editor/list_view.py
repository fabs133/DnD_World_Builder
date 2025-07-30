# trigger_editor/list_view.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QLabel

class TriggerListView(QWidget):
    """
    A QWidget subclass that displays a list of triggers associated with a given object.

    This view provides a label and a QListWidget to show the triggers attached to a tile or entity.
    The context (object) can be set via :meth:`set_context`, which will populate the list with trigger labels.
    """

    def __init__(self):
        """
        Initialize the TriggerListView widget.

        Sets up the layout with a label and a QListWidget for displaying triggers.
        """
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Triggers on this tile or entity:"))
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

    def set_context(self, obj):
        """
        Set the context object and update the trigger list.

        Parameters
        ----------
        obj : object
            The object whose ``triggers`` attribute (an iterable of objects with a ``label`` attribute)
            will be displayed in the list widget.
        """
        self.list_widget.clear()
        for trig in getattr(obj, "triggers", []):
            self.list_widget.addItem(trig.label)

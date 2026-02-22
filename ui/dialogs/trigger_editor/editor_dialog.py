from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget,
)
from .graph_view import TriggerGraphView
from .property_editor import TriggerPropertyEditor
from .list_view import TriggerListView


class TriggerEditorDialog(QDialog):
    """
    Dialog window for editing triggers associated with a tile or entity.

    Presents three tabs — Graph, Properties, and Triggers — with a shared
    button row for creating, saving, and deleting triggers.

    Parameters
    ----------
    tile_data_or_entity : object
        The tile data or entity whose triggers are being edited.
    """

    def __init__(self, tile_data_or_entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Trigger Editor")
        self.setMinimumSize(900, 650)
        self.resize(1000, 700)
        self._context = tile_data_or_entity

        layout = QVBoxLayout(self)

        # --- Tab widget ---
        self.tabs = QTabWidget()
        self.graph_view = TriggerGraphView()
        self.property_editor = TriggerPropertyEditor()
        self.list_view = TriggerListView()

        self.tabs.addTab(self.graph_view, "Graph")
        self.tabs.addTab(self.property_editor, "Properties")
        self.tabs.addTab(self.list_view, "Triggers")
        layout.addWidget(self.tabs)

        # --- Button row ---
        btn_row = QHBoxLayout()
        self.new_btn    = QPushButton("New Trigger")
        self.save_btn   = QPushButton("Save Trigger")
        self.delete_btn = QPushButton("Delete Trigger")
        for b in (self.new_btn, self.save_btn, self.delete_btn):
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

        # --- Wire signals ---
        self.new_btn.clicked.connect(self._on_new_trigger)
        self.save_btn.clicked.connect(self._on_save_trigger)
        self.delete_btn.clicked.connect(self._on_delete_trigger)
        self.graph_view.node_selected.connect(self._on_node_selected)

        # --- Load initial data ---
        self.graph_view.set_context(tile_data_or_entity)
        self.property_editor.set_context(tile_data_or_entity)
        self.list_view.set_context(tile_data_or_entity)

    # ------------------------------------------------------------------
    # Slot implementations
    # ------------------------------------------------------------------

    def _on_new_trigger(self):
        self.property_editor.clear_inputs()
        self.property_editor.set_defaults()
        self.property_editor.set_trigger(None)
        self.tabs.setCurrentWidget(self.property_editor)

    def _on_save_trigger(self):
        self.property_editor.save_trigger()
        self.graph_view.refresh()
        self.list_view.set_context(self._context)

    def _on_node_selected(self, trigger):
        self.property_editor.set_trigger(trigger)
        self.tabs.setCurrentWidget(self.property_editor)

    def _on_delete_trigger(self):
        trigger = self.property_editor.trigger
        if trigger is None:
            return
        triggers = getattr(self._context, "triggers", [])
        self._context.triggers = [t for t in triggers if t.label != trigger.label]
        self.property_editor.set_trigger(None)
        self.graph_view.refresh()
        self.list_view.set_context(self._context)

    # ------------------------------------------------------------------
    # Legacy compat — kept so existing call-sites don't break
    # ------------------------------------------------------------------

    def create_new_trigger(self):
        self._on_new_trigger()

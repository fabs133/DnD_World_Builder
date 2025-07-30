from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton
from .editor_stack import TriggerEditorStack


class TriggerEditorDialog(QDialog):
    """
    Dialog window for editing triggers associated with a tile or entity.
    This dialog provides a user interface for viewing, creating, and editing triggers.
    It contains a stack widget for trigger editing and a button to add new triggers.
    Parameters
    ----------
    tile_data_or_entity : object
        The tile data or entity to associate with the trigger editor context.
    *args : tuple
        Additional positional arguments passed to the QDialog constructor.
    **kwargs : dict
        Additional keyword arguments passed to the QDialog constructor.
    Attributes
    ----------
    editor_stack : TriggerEditorStack
        The stack widget managing the trigger list and property editor views.
    add_trigger_btn : QPushButton
        Button to create a new trigger.
    Methods
    -------
    create_new_trigger()
        Clears the property editor and switches to the trigger creation view.
    """
    def __init__(self, tile_data_or_entity, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Trigger Editor")
        layout = QVBoxLayout(self)

        self.editor_stack = TriggerEditorStack()
        self.editor_stack.set_context(tile_data_or_entity)
        layout.addWidget(self.editor_stack)

        self.add_trigger_btn = QPushButton("New Trigger")
        self.add_trigger_btn.clicked.connect(self.create_new_trigger)
        layout.addWidget(self.add_trigger_btn)


        self.editor_stack.show_list_view()

    def create_new_trigger(self):
        self.editor_stack.property_editor.clear_inputs()
        self.editor_stack.property_editor.set_defaults()
        self.editor_stack.property_editor.set_trigger(None)  # ⬅️ this is a nice-to-have
        self.editor_stack.setCurrentWidget(self.editor_stack.property_editor)


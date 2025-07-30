from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from core.gameCreation.event_bus import EventBus  # Assuming EventBus is defined in event_bus.py

class TriggerEditorDialog(QDialog):
    """
    Dialog for displaying and managing active triggers.

    Allows users to view all registered triggers and remove them if desired.
    """

    def __init__(self, registry):
        """
        Initialize the TriggerEditorDialog.

        :param registry: The registry object that manages triggers.
        """
        super().__init__()
        self.registry = registry
        self.setWindowTitle("Active Triggers")
        layout = QVBoxLayout()

        for trigger in self.registry.get_all_triggers():
            row = QHBoxLayout()
            row.addWidget(QLabel(f"Event: {trigger.event_type}"))
            row.addWidget(QLabel(f"Source: {trigger.source}"))
            # capture the “reaction name” robustly
            reaction_name = getattr(trigger.reaction, "__name__", trigger.reaction.__class__.__name__)
            row.addWidget(QLabel(f"Reaction: {reaction_name}"))

            remove_btn = QPushButton("Remove")
            remove_btn.clicked.connect(lambda _, t=trigger: self.remove_trigger(t))
            row.addWidget(remove_btn)

            layout.addLayout(row)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        self.setLayout(layout)

    def remove_trigger(self, trigger):
        """
        Remove a trigger from the registry and unsubscribe it from the event bus.

        This method also refreshes the dialog to reflect the changes.

        :param trigger: The trigger object to remove.
        """
        EventBus.unsubscribe(trigger.event_type, trigger.check_and_react)
        self.registry.remove_trigger(trigger)
        self.close()
        self.__init__(self.registry)  # Refresh dialog
        self.exec_()

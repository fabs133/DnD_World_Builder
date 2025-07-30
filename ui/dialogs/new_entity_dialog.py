# dialogs/new_entity_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton
)
from models.entities.game_entity import GameEntity  # adjust if it's under models.entity
from registries.trigger_presets import trigger_presets  # adjust if it's under models.triggers

class NewEntityDialog(QDialog):
    """
    Dialog window for creating a new game entity.

    This dialog allows the user to input a name and select a type for a new entity.
    Upon confirmation, a :class:`GameEntity` instance is created and default triggers are attached
    based on the selected entity type.

    Attributes
    ----------
    entity : GameEntity or None
        The created entity instance, or None if creation was cancelled.
    name_input : QLineEdit
        Input field for the entity's name.
    type_input : QComboBox
        Dropdown for selecting the entity's type.
    """

    def __init__(self):
        """
        Initialize the NewEntityDialog.

        Sets up the dialog layout, input fields, and the create button.
        """
        super().__init__()
        self.setWindowTitle("Create New Entity")

        self.entity = None
        layout = QVBoxLayout()
        form = QFormLayout()

        self.name_input = QLineEdit()
        self.type_input = QComboBox()
        self.type_input.addItems(["player", "npc", "enemy", "trap", "object"])

        form.addRow("Name:", self.name_input)
        form.addRow("Type:", self.type_input)

        layout.addLayout(form)

        add_btn = QPushButton("Create Entity")
        add_btn.clicked.connect(self.accept_entity)
        layout.addWidget(add_btn)

        self.setLayout(layout)

    def accept_entity(self):
        """
        Accept the entity creation if the input is valid.

        Creates a :class:`GameEntity` with the provided name and type, attaches default triggers,
        and closes the dialog.
        """
        name = self.name_input.text().strip()
        etype = self.type_input.currentText()

        if name:
            self.entity = GameEntity(name, etype)
            
            # Attach default triggers (if any)
            for t in trigger_presets.get(etype, []):
                self.entity.register_trigger(t)

            self.accept()

    def get_entity(self):
        """
        Get the created entity.

        Returns
        -------
        GameEntity or None
            The created entity instance, or None if no entity was created.
        """
        return self.entity

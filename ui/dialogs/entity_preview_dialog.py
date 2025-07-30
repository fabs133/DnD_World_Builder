from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QTextEdit, QComboBox, QPushButton
from models.entities.game_entity import GameEntity

class EntityPreviewDialog(QDialog):
    """
    A dialog window for previewing and editing a GameEntity's properties.

    Allows the user to view and modify the entity's name, type, stats, and abilities.
    The dialog provides editable fields for each property and returns an updated
    GameEntity instance upon confirmation.

    :param entity: The entity to preview and edit.
    :type entity: GameEntity
    :param parent: The parent widget of the dialog (default is None).
    :type parent: QWidget, optional

    :ivar entity: The entity being previewed and edited.
    :vartype entity: GameEntity
    :ivar name_input: Input field for the entity's name.
    :vartype name_input: QLineEdit
    :ivar type_input: Dropdown for selecting the entity's type.
    :vartype type_input: QComboBox
    :ivar stat_inputs: Dictionary mapping stat names to their corresponding QLineEdit fields.
    :vartype stat_inputs: dict
    :ivar abilities_box: Text box for editing the entity's abilities/inventory.
    :vartype abilities_box: QTextEdit
    """
    def __init__(self, entity: GameEntity, parent=None):
        """
        Initialize the EntityPreviewDialog.

        :param entity: The entity to preview and edit.
        :type entity: GameEntity
        :param parent: The parent widget of the dialog (default is None).
        :type parent: QWidget, optional
        """
        super().__init__(parent)
        self.setWindowTitle("Preview and Edit Entity")
        self.entity = entity

        layout = QFormLayout()
        self.setLayout(layout)

        # Editable name and type
        self.name_input = QLineEdit(entity.name)
        layout.addRow("Name:", self.name_input)

        self.type_input = QComboBox()
        self.type_input.addItems(["enemy", "npc", "player", "trap", "object"])
        self.type_input.setCurrentText(entity.entity_type)
        layout.addRow("Type:", self.type_input)

        # Stats editor (flattened for simplicity)
        self.stat_inputs = {}
        for key, value in entity.stats.items():
            stat_field = QLineEdit(str(value))
            layout.addRow(f"{key.upper()}:", stat_field)
            self.stat_inputs[key] = stat_field

        # Abilities (as single block of text for now)
        self.abilities_box = QTextEdit("\n".join(entity.inventory))
        layout.addRow("Abilities:", self.abilities_box)

        # Confirm button
        confirm_btn = QPushButton("Confirm")
        confirm_btn.clicked.connect(self.accept)
        layout.addRow(confirm_btn)

    def get_entity(self) -> GameEntity:
        """
        Retrieve an updated GameEntity instance based on the current dialog inputs.

        :return: The updated entity with values from the dialog fields.
        :rtype: GameEntity
        """
        updated_stats = {
            key: self._safe_cast(field.text())
            for key, field in self.stat_inputs.items()
        }
        updated_inventory = self.abilities_box.toPlainText().splitlines()
        return GameEntity(
            name=self.name_input.text(),
            entity_type=self.type_input.currentText(),
            stats=updated_stats,
            inventory=updated_inventory,
        )

    def _safe_cast(self, value):
        """
        Safely cast a string value to int or float if possible, otherwise return as string.

        :param value: The value to cast.
        :type value: str
        :return: The value cast to int or float if possible, otherwise the original string.
        :rtype: int, float, or str
        """
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value

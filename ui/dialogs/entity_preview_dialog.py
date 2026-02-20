from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QTextEdit, QComboBox, QPushButton,
    QLabel, QFileDialog, QHBoxLayout,
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from models.entities.game_entity import GameEntity


class EntityPreviewDialog(QDialog):
    """
    A dialog window for previewing and editing a GameEntity's properties.

    Allows the user to view and modify the entity's name, type, stats, abilities,
    and portrait image. The dialog provides editable fields for each property and
    returns an updated GameEntity instance upon confirmation.

    :param entity: The entity to preview and edit.
    :type entity: GameEntity
    :param parent: The parent widget of the dialog (default is None).
    :type parent: QWidget, optional
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
        self._image_path = getattr(entity, "image_path", None)

        layout = QFormLayout()
        self.setLayout(layout)

        # Portrait image preview
        self.image_label = QLabel()
        self.image_label.setFixedSize(128, 128)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #ccc; background: #f5f5f5;")
        self._update_image_preview()

        image_btn = QPushButton("Choose Image...")
        image_btn.clicked.connect(self._pick_image)
        clear_image_btn = QPushButton("Clear")
        clear_image_btn.clicked.connect(self._clear_image)

        image_row = QHBoxLayout()
        image_row.addWidget(self.image_label)
        image_btn_col = QHBoxLayout()
        image_btn_col.addWidget(image_btn)
        image_btn_col.addWidget(clear_image_btn)
        image_row.addLayout(image_btn_col)
        layout.addRow("Portrait:", image_row)

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

    def _pick_image(self):
        """Open a file dialog to select a portrait image."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Portrait Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if path:
            self._image_path = path
            self._update_image_preview()

    def _clear_image(self):
        """Clear the portrait image."""
        self._image_path = None
        self._update_image_preview()

    def _update_image_preview(self):
        """Update the portrait preview label."""
        if self._image_path:
            pixmap = QPixmap(self._image_path)
            if not pixmap.isNull():
                self.image_label.setPixmap(
                    pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                return
        self.image_label.setText("No image")

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
        entity = GameEntity(
            name=self.name_input.text(),
            entity_type=self.type_input.currentText(),
            stats=updated_stats,
            inventory=updated_inventory,
            image_path=self._image_path,
        )
        return entity

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

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QToolButton, QMenu
from PyQt5.QtCore import pyqtSignal


class EntityListItem(QWidget):
    """
    Custom widget for a single row in the entity list.

    Shows the entity name and type plus a ⋮ menu button for Edit / Delete / Duplicate.

    Signals:
        edit_requested(entity)
        delete_requested(entity)
        duplicate_requested(entity)
    """

    edit_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object)
    duplicate_requested = pyqtSignal(object)

    def __init__(self, entity, parent=None):
        super().__init__(parent)
        self.entity = entity

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self.name_label = QLabel(f"{entity.name}  ({entity.entity_type})")
        layout.addWidget(self.name_label)
        layout.addStretch()

        menu_btn = QToolButton()
        menu_btn.setText("⋮")
        menu_btn.setStyleSheet("QToolButton::menu-indicator { image: none; }")
        menu_btn.setPopupMode(QToolButton.InstantPopup)

        menu = QMenu()
        menu.addAction("Edit", lambda: self.edit_requested.emit(self.entity))
        menu.addAction("Delete", lambda: self.delete_requested.emit(self.entity))
        menu.addAction("Duplicate", lambda: self.duplicate_requested.emit(self.entity))
        menu_btn.setMenu(menu)

        layout.addWidget(menu_btn)

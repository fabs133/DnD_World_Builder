from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QColorDialog,
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt


class ColorModeDialog(QDialog):
    """
    Small dialog for picking a paint color and toggling Color Mode.

    After exec_(), read :attr:`color` and :attr:`color_mode` for the result.

    :param current_color: Initial hex color string (e.g. ``"#CCCCCC"``).
    :param color_mode_active: Whether Color Mode is currently on.
    :param parent: Parent widget.
    """

    def __init__(self, current_color="#CCCCCC", color_mode_active=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Color Mode")
        self.setFixedWidth(300)

        self.color = current_color
        self.color_mode = color_mode_active

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- Color preview + pick button ---
        self._preview = QLabel()
        self._preview.setFixedSize(60, 60)
        self._preview.setAlignment(Qt.AlignCenter)
        self._update_preview()

        pick_btn = QPushButton("Pick Color...")
        pick_btn.clicked.connect(self._pick_color)

        preview_row = QHBoxLayout()
        preview_row.addWidget(self._preview)
        preview_row.addWidget(pick_btn)
        preview_row.addStretch()
        layout.addLayout(preview_row)

        # --- Color Mode toggle ---
        self._mode_cb = QCheckBox("Color Mode — paint tiles on left-click")
        self._mode_cb.setChecked(color_mode_active)
        layout.addWidget(self._mode_cb)

        # --- OK button ---
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

    def accept(self):
        self.color_mode = self._mode_cb.isChecked()
        super().accept()

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self.color), self, "Select Paint Color")
        if c.isValid():
            self.color = c.name()
            self._update_preview()

    def _update_preview(self):
        self._preview.setStyleSheet(
            f"background-color: {self.color}; border: 2px solid #888; border-radius: 4px;"
        )

from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFormLayout, QFileDialog, QSpinBox, QWidget,
    QHBoxLayout, QTextEdit, QCheckBox, QListWidget
)
from core.settings_manager import SettingsManager
from core.logger import AppLogger, app_logger
from ui.dialogs.trigger_editor_dialog import TriggerEditorDialog


class MainMenuDialog(QDialog):
    """
    Dialog for creating or loading a new map.

    Provides input for grid type, size, and buttons to proceed or cancel.
    """
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("DnD Map Editor - New Map Setup")
        self.init_ui()

    def init_ui(self):
        grid_type = self.settings.get("grid_type", "hex")
        grid_size = self.settings.get("grid_size", 30)

        app_logger.debug(f"[MainMenuDialog] Using grid type: {grid_type}, size: {grid_size}")

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Create New Map"))

        self.grid_type_selector = QComboBox()
        self.grid_type_selector.addItems(["square", "hex"])
        self.grid_type_selector.setCurrentText(grid_type)
        layout.addWidget(QLabel("Grid Type:"))
        layout.addWidget(self.grid_type_selector)

        self.rows_input = QSpinBox()
        self.rows_input.setRange(1, 100)
        self.rows_input.setValue(self.settings.get("default_rows", 20))
        layout.addWidget(QLabel("Rows:"))
        layout.addWidget(self.rows_input)

        self.cols_input = QSpinBox()
        self.cols_input.setRange(1, 100)
        self.cols_input.setValue(self.settings.get("default_cols", 20))
        layout.addWidget(QLabel("Columns:"))
        layout.addWidget(self.cols_input)

        # Buttons
        new_map_btn = QPushButton("Create New Map")
        new_map_btn.clicked.connect(self.create_new_map)
        layout.addWidget(new_map_btn)

        load_map_btn = QPushButton("Load Map")
        load_map_btn.clicked.connect(self.load_map)
        layout.addWidget(load_map_btn)

        trigger_editor_btn = QPushButton("Trigger Registry")
        trigger_editor_btn.clicked.connect(self.open_trigger_editor)
        layout.addWidget(trigger_editor_btn)

        quit_btn = QPushButton("Cancel")
        quit_btn.clicked.connect(self.exit_and_save)
        layout.addWidget(quit_btn)

        self.setLayout(layout)

    def create_new_map(self):
        """
        Save preferences and accept the dialog (signal success).
        """
        self.settings["grid_type"] = self.grid_type_selector.currentText()
        self.settings["default_rows"] = self.rows_input.value()
        self.settings["default_cols"] = self.cols_input.value()
        self.settings.save_settings()
        self.accept()

    def load_map(self):
        """
        Let the user select a map file and update the recent files list.
        """
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Map", "", "Map Files (*.json)")
        if file_path:
            recent = self.settings.get("recent_files", [])
            if file_path in recent:
                recent.remove(file_path)
            recent.insert(0, file_path)
            self.settings.set("recent_files", recent[:5])
            self.settings.save_settings()
            self.accept()  # still exit the dialog; caller should handle loading

    def open_trigger_editor(self):
        """
        Launch the trigger registry editor.
        """
        from registries.trigger_registry import global_trigger_registry
        dlg = TriggerEditorDialog(global_trigger_registry)
        dlg.exec_()

    def exit_and_save(self):
        """
        Save settings and reject the dialog (signal cancel).
        """
        self.settings.save_settings()
        self.reject()


# Optional standalone test launcher
if __name__ == '__main__':
    logger = AppLogger().get_logger()
    logger.info("Starting standalone MainMenuDialog...")

    app = QApplication(sys.argv)
    settings = SettingsManager()

    dlg = MainMenuDialog(settings)
    if dlg.exec_() == QDialog.Accepted:
        print("[Launcher] User accepted dialog.")
    else:
        print("[Launcher] User cancelled dialog.")

    sys.exit(0)

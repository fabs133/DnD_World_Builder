from PyQt5.QtWidgets import QMainWindow, QStackedWidget
from ui.main_window import MainWindow
from ui.scenario_overview import ScenarioOverviewWidget
from core.settings_manager import SettingsManager


class MainController(QMainWindow):
    """
    Main application controller for the DnD Project.

    Manages the main window, scenario overview, and map editor widgets.
    Handles switching between scenario overview and map editor.
    """

    def __init__(self):
        """
        Initialize the MainController window, settings manager, and UI stack.
        """
        super().__init__()
        self.setWindowTitle("DnD Project")
        self.setGeometry(100, 100, 1200, 800)

        self.settings = SettingsManager()
        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)

        # Scenario Overview
        self.scenario_overview = ScenarioOverviewWidget(
            map_loader=self.load_existing_map,
            settings_manager=self.settings
        )
        self.scenario_overview.new_btn.clicked.connect(self.start_new_map)
        self.stack.addWidget(self.scenario_overview)

        # Editor (hidden at first)
        self.map_editor = None  # Will be created when needed

    def start_new_map(self):
        """
        Start a new map editing session.

        Removes any existing map editor widget, creates a new one,
        and switches the UI to the map editor.
        """
        # TODO: Show a QDialog to input name + meta (optional)
        if self.map_editor is not None:
            self.stack.removeWidget(self.map_editor)
            self.map_editor.deleteLater()

        self.map_editor = MainWindow(self.settings)
        # expose the SettingsManager to the tests
        self.map_editor.settings_manager = self.settings
        self.map_editor.initialize_default_map()
        self.stack.addWidget(self.map_editor)
        self.stack.setCurrentWidget(self.map_editor)

    def load_existing_map(self, map_path):
        """
        Load an existing map into the editor.

        Removes any existing map editor widget, creates a new one,
        loads the map from the given path, and switches the UI to the map editor.

        Parameters
        ----------
        map_path : str
            The file path to the map to be loaded.
        """
        if self.map_editor is not None:
            self.stack.removeWidget(self.map_editor)
            self.map_editor.deleteLater()

        self.map_editor = MainWindow(self.settings)
        # expose the SettingsManager and remember what we loaded
        self.map_editor.settings_manager = self.settings
        self.map_editor.loaded_path = str(map_path)
        self.map_editor.load_map_from_file(str(map_path))
        self.stack.addWidget(self.map_editor)
        self.stack.setCurrentWidget(self.map_editor)

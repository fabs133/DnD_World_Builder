import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QComboBox, QLabel
from core.gameCreation.main_controller import MainController
from core.characterCreation.character_gui import CharacterCreationWindow
from core.settings_manager import SettingsManager
from qt_material import apply_stylesheet, list_themes


# Map user-friendly names to qt-material theme files
THEME_MAP = {
    "Dark Amber": "dark_amber.xml",
    "Dark Blue": "dark_blue.xml",
    "Dark Cyan": "dark_cyan.xml",
    "Dark Green": "dark_lightgreen.xml",
    "Dark Pink": "dark_pink.xml",
    "Dark Purple": "dark_purple.xml",
    "Dark Red": "dark_red.xml",
    "Dark Teal": "dark_teal.xml",
    "Dark Yellow": "dark_yellow.xml",
    "Light Amber": "light_amber.xml",
    "Light Blue": "light_blue.xml",
    "Light Cyan": "light_cyan.xml",
    "Light Green": "light_lightgreen.xml",
    "Light Orange": "light_orange.xml",
    "Light Pink": "light_pink.xml",
    "Light Purple": "light_purple.xml",
    "Light Red": "light_red.xml",
    "Light Teal": "light_teal.xml",
    "Light Yellow": "light_yellow.xml",
}


def apply_theme(app, theme_file):
    """Apply a qt-material theme to the application.

    :param app: The QApplication instance.
    :param theme_file: The theme XML filename (e.g., 'dark_teal.xml').
    """
    if theme_file in list_themes():
        apply_stylesheet(app, theme=theme_file)
    else:
        apply_stylesheet(app, theme="dark_teal.xml")


class LaunchDialog(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.setWindowTitle("DnD Project - Launcher")
        self.setFixedSize(320, 220)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        game_button = QPushButton("Open Game Creation")
        game_button.clicked.connect(self.launch_game_creation)
        layout.addWidget(game_button)

        character_button = QPushButton("Open Character Creator")
        character_button.clicked.connect(self.launch_character_creator)
        layout.addWidget(character_button)

        layout.addSpacing(10)
        layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEME_MAP.keys())

        # Select the currently saved theme
        current_theme = self.settings.get("theme", "dark_teal.xml")
        for name, filename in THEME_MAP.items():
            if filename == current_theme:
                self.theme_combo.setCurrentText(name)
                break

        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        layout.addWidget(self.theme_combo)

    def _on_theme_changed(self, theme_name):
        theme_file = THEME_MAP.get(theme_name, "dark_teal.xml")
        self.settings.set("theme", theme_file)
        apply_theme(QApplication.instance(), theme_file)

    def launch_game_creation(self):
        self.main_controller = MainController()
        self.main_controller.show()
        self.close()

    def launch_character_creator(self):
        self.char_window = CharacterCreationWindow()
        self.char_window.show()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    settings = SettingsManager()
    theme_file = settings.get("theme", "dark_teal.xml")
    apply_theme(app, theme_file)

    launcher = LaunchDialog(settings)
    launcher.show()
    sys.exit(app.exec_())
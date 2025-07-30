import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from core.gameCreation.main_controller import MainController
from core.characterCreation.character_gui import CharacterCreationWindow

class LaunchDialog(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DnD Project - Launcher")
        self.setFixedSize(300, 150)
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
    launcher = LaunchDialog()
    launcher.show()
    sys.exit(app.exec_())
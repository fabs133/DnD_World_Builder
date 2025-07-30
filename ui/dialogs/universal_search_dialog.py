# dialogs/universal_search_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
    QLineEdit, QListWidget, QPushButton, QLabel, QMessageBox
)
from core.rulebook.import_manager import RulebookImporter
from .entity_preview_dialog import EntityPreviewDialog

class UniversalSearchDialog(QDialog):
    """
    A dialog for searching and importing entities (e.g., monsters, spells) from a rulebook.

    Allows the user to select a category (such as "Monster" or "Spell"), search for entities by name,
    preview their details, and import them into the application.

    :param mode: The initial category to search in ("monster" or "spell"). Defaults to "monster".
    :type mode: str, optional
    :param args: Additional positional arguments passed to QDialog.
    :param kwargs: Additional keyword arguments passed to QDialog.

    :ivar importer: The importer used to search and import entities from the rulebook.
    :vartype importer: RulebookImporter
    :ivar mode: The current search category ("monster" or "spell").
    :vartype mode: str
    :ivar category_selector: Dropdown for selecting the entity category.
    :vartype category_selector: QComboBox
    :ivar search_input: Input field for typing search queries.
    :vartype search_input: QLineEdit
    :ivar result_list: List widget displaying search results.
    :vartype result_list: QListWidget
    :ivar import_btn: Button to import the selected entity.
    :vartype import_btn: QPushButton
    :ivar cancel_btn: Button to cancel and close the dialog.
    :vartype cancel_btn: QPushButton
    :ivar selected_object: The imported and possibly converted entity selected by the user (set after successful import).
    :vartype selected_object: object
    """

    def __init__(self, mode="monster", *args, **kwargs):
        """
        Initialize the UniversalSearchDialog.

        :param mode: The initial category to search in ("monster" or "spell"). Defaults to "monster".
        :type mode: str, optional
        :param args: Additional positional arguments passed to QDialog.
        :param kwargs: Additional keyword arguments passed to QDialog.
        """
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Search Rulebook")
        self.resize(400, 300)
        self.importer = RulebookImporter()
        self.mode = mode  # default "monster", can be "spell" etc.

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Mode selector
        mode_row = QHBoxLayout()
        self.category_selector = QComboBox()
        self.category_selector.addItems(["Monster", "Spell"])
        self.category_selector.setCurrentText(mode.capitalize())
        self.category_selector.currentTextChanged.connect(self.load_suggestions)
        mode_row.addWidget(QLabel("Category:"))
        mode_row.addWidget(self.category_selector)
        self.layout.addLayout(mode_row)

        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to search...")
        self.search_input.textChanged.connect(self.filter_list)
        self.layout.addWidget(self.search_input)

        # Results
        self.result_list = QListWidget()
        self.layout.addWidget(self.result_list)

        # Buttons
        btn_row = QHBoxLayout()
        self.import_btn = QPushButton("Import")
        self.import_btn.clicked.connect(self.import_selected)
        btn_row.addWidget(self.import_btn)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)
        self.layout.addLayout(btn_row)

        self.load_suggestions(self.mode.capitalize())

    def load_suggestions(self, mode):
        """
        Load and display suggestions for the selected category.

        :param mode: The category to load suggestions for ("Monster" or "Spell").
        :type mode: str
        """
        self.mode = mode.lower()
        self.result_list.clear()

        if self.mode == "monster":
            results = self.importer.search_monsters()
        elif self.mode == "spell":
            results = self.importer.search_spells()
        else:
            results = []

        for name in sorted(results):
            self.result_list.addItem(name)

    def filter_list(self, text):
        """
        Filter the displayed list of entities based on the search input.

        :param text: The text to filter the list by.
        :type text: str
        """
        for i in range(self.result_list.count()):
            item = self.result_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def import_selected(self):
        """
        Import the currently selected entity from the list.

        Opens a preview dialog for the selected entity. If the user confirms, the entity is imported
        and stored in ``selected_object``. Displays error dialogs if import fails or no selection is made.
        """
        item = self.result_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No selection", "Please select an item to import.")
            return

        name = item.text()

        # Safe import + conversion
        if self.mode == "monster":
            rulebook_entity = self.importer.import_monster(name)
        elif self.mode == "spell":
            rulebook_entity = self.importer.import_spell(name)
        else:
            rulebook_entity = None

        if not rulebook_entity:
            QMessageBox.critical(self, "Import failed", f"Could not import '{name}'.")
            return

        # 👇 Ensure we convert only if needed
        if hasattr(rulebook_entity, "to_game_entity"):
            game_entity = rulebook_entity.to_game_entity()
        else:
            game_entity = rulebook_entity  # already a GameEntity

        preview = EntityPreviewDialog(game_entity)
        if preview.exec_():
            self.selected_object = preview.get_entity()
            self.accept()

    def get_selected_object(self):
        """
        Get the imported entity selected by the user.

        :return: The imported and possibly converted entity, or None if no selection was made.
        :rtype: object or None
        """
        return getattr(self, "selected_object", None)

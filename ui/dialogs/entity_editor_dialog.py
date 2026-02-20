from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton
from .universal_search_dialog import UniversalSearchDialog  # Assuming this is the correct import path for UniversalSearchDialog
from .trigger_editor.editor_dialog import TriggerEditorDialog

class EntityEditorDialog(QDialog):
    """
    Dialog for editing entities on a specific tile.

    Allows adding, removing, importing, and editing triggers for entities.

    :param tile_data: The tile data object containing entities.
    :type tile_data: object
    """
    def __init__(self, tile_data):
        """
        Initialize the EntityEditorDialog.

        :param tile_data: The tile data object containing entities.
        :type tile_data: object
        """
        super().__init__()
        self.tile_data = tile_data
        self.setWindowTitle("Entities on this tile")
        layout = QVBoxLayout()

        self.entity_list = QListWidget()
        for e in tile_data.entities:
            self.entity_list.addItem(f"{e.name} ({e.entity_type})")
        layout.addWidget(self.entity_list)

        add_btn = QPushButton("Add Entity")
        add_btn.clicked.connect(self.add_entity)
        layout.addWidget(add_btn)

        del_btn = QPushButton("Remove Selected")
        del_btn.clicked.connect(self.remove_entity)
        layout.addWidget(del_btn)

        import_btn = QPushButton("Import from Rulebook")
        import_btn.clicked.connect(self.import_from_rulebook)
        layout.addWidget(import_btn)

        edit_trigger_btn = QPushButton("Edit Triggers for Selected")
        edit_trigger_btn.clicked.connect(self.edit_triggers_for_selected)
        layout.addWidget(edit_trigger_btn)

        stat_block_btn = QPushButton("View Stat Block")
        stat_block_btn.clicked.connect(self.view_stat_block)
        layout.addWidget(stat_block_btn)

        self.setLayout(layout)

    def add_entity(self):
        """
        Open a dialog to add a new entity to the tile.
        """
        from .new_entity_dialog import NewEntityDialog  # upcoming step
        dlg = NewEntityDialog()
        if dlg.exec_():
            entity = dlg.get_entity()
            self.tile_data.add_entity(entity)
            self.entity_list.addItem(f"{entity.name} ({entity.entity_type})")

    def remove_entity(self):
        """
        Remove the currently selected entity from the tile.
        """
        idx = self.entity_list.currentRow()
        if idx >= 0:
            self.tile_data.entities.pop(idx)
            self.entity_list.takeItem(idx)

    def import_from_rulebook(self):
        """
        Import an entity from the rulebook using the UniversalSearchDialog.
        """
        dialog = UniversalSearchDialog(mode="monster")  # or make mode selectable later
        if dialog.exec_():
            entity = dialog.get_selected_object()
            if entity:
                self.tile_data.add_entity(entity)
                self.entity_list.addItem(f"{entity.name} ({entity.entity_type})")

    def view_stat_block(self):
        """
        Open the StatBlockDialog for the currently selected entity.
        """
        idx = self.entity_list.currentRow()
        if idx >= 0:
            entity = self.tile_data.entities[idx]
            from .stat_block_dialog import StatBlockDialog
            dlg = StatBlockDialog(entity, parent=self)
            dlg.exec_()

    def edit_triggers_for_selected(self):
        """
        Open the TriggerEditorDialog for the currently selected entity.
        """
        idx = self.entity_list.currentRow()
        if idx >= 0:
            entity = self.tile_data.entities[idx]
            dlg = TriggerEditorDialog(entity)
            dlg.exec_()
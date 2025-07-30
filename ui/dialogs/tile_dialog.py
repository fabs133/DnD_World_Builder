from PyQt5.QtWidgets import QDialog, QFormLayout, QLabel, QLineEdit, QComboBox, QVBoxLayout, QPushButton, QTextEdit, QCheckBox
from PyQt5.QtCore import Qt
from models.tiles.tile_data import TileTag, TerrainType, TileData
from .entity_editor_dialog import EntityEditorDialog  # Assuming this is the correct import path for EntityEditorDialog
from .trigger_editor.editor_dialog import TriggerEditorDialog  # import this near the top
from PyQt5.QtWidgets import QColorDialog
from PyQt5.QtGui import QColor
from .tile_edit.tile_edit_command import TileEditCommand

class TileDialog(QDialog):
    """
    Dialog for viewing and editing the attributes of a tile.

    This dialog allows users to view and modify various properties of a tile, such as terrain type, tags, user label, note, overlay color, and associated entities and triggers. It also provides undo functionality by saving the original state and pushing changes to the main window's undo stack.

    Parameters
    ----------
    tile_data : TileData
        The TileData instance representing the tile to be edited.
    main_window : QMainWindow, optional
        Reference to the main application window, used for undo stack integration.
    tile_item : QGraphicsItem, optional
        The graphical item representing the tile in the scene.
    *args
        Additional positional arguments for QDialog.
    **kwargs
        Additional keyword arguments for QDialog.

    Attributes
    ----------
    tile_data : TileData
        The tile data being edited.
    main_window : QMainWindow or None
        Reference to the main window for undo stack operations.
    tile_item : QGraphicsItem or None
        The graphical item for the tile.
    _original_state : dict
        The original state of the tile data for undo purposes.
    terrain_input : QComboBox
        Dropdown for selecting terrain type.
    tag_checkboxes : dict
        Mapping of TileTag to QCheckBox for tag selection.
    label_input : QLineEdit
        Input for user label.
    note_input : QTextEdit
        Input for tile note.
    overlay_input : QLineEdit
        Input for overlay color (hex).
    color_button : QPushButton
        Button to open color picker dialog.
    entity_preview : QLineEdit
        Read-only preview of associated entities.
    last_updated_label : QLabel
        Label showing last updated timestamp.
    """
    def __init__(self, tile_data, main_window=None, tile_item=None,  *args, **kwargs):
        """
        Initialize the TileDialog.

        Parameters
        ----------
        tile_data : TileData
            The TileData instance representing the tile to be edited.
        main_window : QMainWindow, optional
            Reference to the main application window, used for undo stack integration.
        tile_item : QGraphicsItem, optional
            The graphical item representing the tile in the scene.
        *args
            Additional positional arguments for QDialog.
        **kwargs
            Additional keyword arguments for QDialog.
        """
        super().__init__(*args, **kwargs)
        self.tile_data = tile_data  # Set directly to the passed TileData
        self.setWindowTitle(f"Tile Attributes")
        self.main_window = main_window
        self.tile_item = tile_item
        self._original_state = tile_data.to_dict()  # Save for undo
        layout = QFormLayout()
        self.setLayout(layout)

        # --- READ-ONLY INFO ---
        layout.addRow("Tile ID:", QLabel(self.tile_data.tile_id))
        layout.addRow("Position:", QLabel(str(tile_data.position)))

        # --- TERRAIN ---
        print(f"Debug print: {tile_data.terrain}")
        self.terrain_input = QComboBox()
        self.terrain_input.addItems([t.name for t in TerrainType])
        self.terrain_input.setCurrentText(tile_data.terrain.name)
        layout.addRow("Terrain:", self.terrain_input)

        # --- TAGS ---
        self.tag_checkboxes = {}
        tag_box = QVBoxLayout()
        for tag in TileTag:
            cb = QCheckBox(tag.name.replace("_", " ").title())
            cb.setChecked(tag in tile_data.tags)
            self.tag_checkboxes[tag] = cb
            tag_box.addWidget(cb)
        layout.addRow(QLabel("Tags:"), tag_box)

        inherited_attributes = [attr for attr in dir(tile_data) if not attr.startswith('__') and not callable(getattr(tile_data, attr))]
        print(f"Inherited attributes: {inherited_attributes}")

        # --- LABEL ---
        self.label_input = QLineEdit(tile_data.user_label or "")
        layout.addRow("User Label:", self.label_input)

        # --- NOTE ---
        self.note_input = QTextEdit(tile_data.note or "")
        layout.addRow("Note:", self.note_input)

        # --- OVERLAY COLOR ---
        from PyQt5.QtWidgets import QHBoxLayout

        self.overlay_input = QLineEdit(tile_data.overlay_color or "#CCCCCC")
        self.color_button = QPushButton("Pick Color")
        self.color_button.clicked.connect(self.open_color_picker)

        overlay_layout = QHBoxLayout()
        overlay_layout.addWidget(self.overlay_input)
        overlay_layout.addWidget(self.color_button)
        layout.addRow("Overlay Color (Hex):", overlay_layout)

        # --- ENTITIES ---
        self.entity_preview = QLineEdit(", ".join(e.name for e in tile_data.entities))
        self.entity_preview.setReadOnly(True)
        layout.addRow("Entities (read-only):", self.entity_preview)

        # --- LAST UPDATED ---
        self.last_updated_label = QLabel(tile_data.last_updated or "None")
        layout.addRow("Last Updated:", self.last_updated_label)

        # --- SAVE BUTTON ---
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_attributes)
        layout.addRow(save_btn)

        entity_btn = QPushButton("Edit Entities...")
        entity_btn.clicked.connect(self.edit_entities)
        layout.addRow(entity_btn)

        self.color_button = QPushButton("Pick Color")
        self.color_button.clicked.connect(self.open_color_picker)

        # --- TRIGGERS ---
        trigger_btn = QPushButton("Edit Triggers...")
        trigger_btn.clicked.connect(self.edit_triggers)
        layout.addRow(trigger_btn)

    def edit_entities(self):
        """
        Open the entity editor dialog for this tile.
        """
        dlg = EntityEditorDialog(self.tile_data)
        dlg.exec_()

    def save_attributes(self):
        """
        Save the current attributes to the tile data and push an undo command if applicable.
        """
        td = self.tile_data

        # Apply changes
        td.terrain = TerrainType[self.terrain_input.currentText()]
        td.tags = [tag for tag, cb in self.tag_checkboxes.items() if cb.isChecked()]
        td.user_label = self.label_input.text()
        td.note = self.note_input.toPlainText()
        td.overlay_color = self.overlay_input.text()

        from datetime import datetime
        td.last_updated = datetime.now().isoformat()

        new_state = td.to_dict()
        
        if self.main_window:
            cmd = TileEditCommand(td, self._original_state, new_state, tile_item=self.tile_item)
            self.main_window.undo_stack.push(cmd)

        self.accept()

    def open_color_picker(self):
        """
        Open a color picker dialog to select overlay color.
        """
        initial = QColor(self.overlay_input.text() or "#CCCCCC")
        color = QColorDialog.getColor(initial, self, "Select Overlay Color")
        if color.isValid():
            hex_color = color.name()
            self.overlay_input.setText(hex_color)
            self.update_tile_overlay_preview(hex_color)

    def update_tile_overlay_preview(self, hex_color):
        """
        Update the overlay color preview for the tile item.

        Parameters
        ----------
        hex_color : str
            The hex color string to set as the overlay color.
        """
        tile_item = getattr(self.tile_data, "tile_item", None)
        if tile_item:
            tile_item.set_overlay_color(hex_color)

    def edit_triggers(self):
        """
        Open the trigger editor dialog for this tile.
        """
        dlg = TriggerEditorDialog(self.tile_data)
        dlg.exec_()

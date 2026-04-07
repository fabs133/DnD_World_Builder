from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLabel, QLineEdit, QComboBox, QVBoxLayout,
    QPushButton, QTextEdit, QCheckBox, QColorDialog, QHBoxLayout,
    QFileDialog, QGroupBox, QMessageBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPixmap, QImageReader
from models.tiles.tile_data import TileTag, TerrainType, TileData
from core.logger import app_logger
from .entity_editor_dialog import EntityEditorDialog
from .trigger_editor.editor_dialog import TriggerEditorDialog
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
        app_logger.debug(f"Tile terrain: {tile_data.terrain}")
        self.terrain_input = QComboBox()
        self.terrain_input.addItems([t.name for t in TerrainType])
        self.terrain_input.setCurrentText(tile_data.terrain.name)
        layout.addRow("Terrain:", self.terrain_input)

        # --- TAGS ---
        self.tag_checkboxes = {}
        tag_group = QGroupBox("Tags")
        tag_layout = QVBoxLayout(tag_group)
        for tag in TileTag:
            cb = QCheckBox(tag.name.replace("_", " ").title())
            cb.setChecked(tag in tile_data.tags)
            cb.setStyleSheet("""
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 2px solid #888;
                    border-radius: 3px;
                    background: transparent;
                }
                QCheckBox::indicator:checked {
                    background-color: #6d4c9e;
                    border-color: #c084fc;
                }
            """)
            self.tag_checkboxes[tag] = cb
            tag_layout.addWidget(cb)
        layout.addRow(tag_group)

        inherited_attributes = [attr for attr in dir(tile_data) if not attr.startswith('__') and not callable(getattr(tile_data, attr))]
        app_logger.debug(f"Inherited attributes: {inherited_attributes}")

        # --- LABEL ---
        self.label_input = QLineEdit(tile_data.user_label or "")
        layout.addRow("User Label:", self.label_input)

        # --- ENCOUNTER ZONE ---
        self.zone_id_input = QLineEdit(tile_data.zone_id or "")
        self.zone_id_input.setPlaceholderText("e.g. Guard Post, Main Hall")
        layout.addRow("Encounter Zone:", self.zone_id_input)

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

        # --- BACKGROUND IMAGE ---
        self._background_image_path = tile_data.background_image
        self.bg_image_label = QLabel()
        self.bg_image_label.setFixedSize(100, 100)
        self.bg_image_label.setAlignment(Qt.AlignCenter)
        from core import theme_palette as tp
        self.bg_image_label.setStyleSheet(
            f"border: 1px solid {tp.get_themed('border_secondary')}; "
            f"background: {tp.get_themed('bg_secondary')};"
        )
        self._update_bg_image_preview()

        bg_btn = QPushButton("Choose Image...")
        bg_btn.clicked.connect(self._pick_background_image)
        bg_clear_btn = QPushButton("Clear")
        bg_clear_btn.clicked.connect(self._clear_background_image)

        bg_row = QHBoxLayout()
        bg_row.addWidget(self.bg_image_label)
        bg_btns = QHBoxLayout()
        bg_btns.addWidget(bg_btn)
        bg_btns.addWidget(bg_clear_btn)
        bg_row.addLayout(bg_btns)
        layout.addRow("Background Image:", bg_row)

        # --- AMBIENT AUDIO ---
        self._ambient_audio_path = tile_data.ambient_audio
        self.audio_path_label = QLineEdit(tile_data.ambient_audio or "")
        self.audio_path_label.setReadOnly(True)

        audio_btn = QPushButton("Choose Audio...")
        audio_btn.clicked.connect(self._pick_ambient_audio)
        audio_clear_btn = QPushButton("Clear")
        audio_clear_btn.clicked.connect(self._clear_ambient_audio)

        audio_play_btn = QPushButton("Play")
        audio_play_btn.clicked.connect(self._play_ambient_audio)
        audio_stop_btn = QPushButton("Stop")
        audio_stop_btn.clicked.connect(self._stop_ambient_audio)

        audio_row = QHBoxLayout()
        audio_row.addWidget(self.audio_path_label)
        audio_row.addWidget(audio_btn)
        audio_row.addWidget(audio_clear_btn)
        audio_row.addWidget(audio_play_btn)
        audio_row.addWidget(audio_stop_btn)
        layout.addRow("Ambient Audio:", audio_row)

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

        # --- START ZONE exclusivity: only one tile per scenario ---
        was_start_zone = "START_ZONE" in self._original_state.get("tags", [])
        will_be_start_zone = self.tag_checkboxes[TileTag.START_ZONE].isChecked()
        if will_be_start_zone and not was_start_zone and self.tile_item:
            scene = self.tile_item.scene() if hasattr(self.tile_item, "scene") else None
            if scene:
                for item in scene.items():
                    if hasattr(item, "tile_data") and item is not self.tile_item:
                        if TileTag.START_ZONE in item.tile_data.tags:
                            QMessageBox.warning(
                                self, "Start Zone Conflict",
                                "Another tile is already marked as the Start Zone.\n"
                                "Only one Start Zone is allowed per scenario.\n\n"
                                "Remove the existing Start Zone tag first."
                            )
                            self.tag_checkboxes[TileTag.START_ZONE].setChecked(False)
                            return

        # Apply changes
        td.terrain = TerrainType[self.terrain_input.currentText()]
        td.tags = [tag for tag, cb in self.tag_checkboxes.items() if cb.isChecked()]
        td.user_label = self.label_input.text()
        td.zone_id = self.zone_id_input.text().strip() or None
        td.note = self.note_input.toPlainText()
        td.overlay_color = self.overlay_input.text()
        td.background_image = self._background_image_path
        td.ambient_audio = self._ambient_audio_path

        from datetime import datetime
        td.last_updated = datetime.now().isoformat()

        new_state = td.to_dict()
        
        if self.main_window:
            cmd = TileEditCommand(td, self._original_state, new_state, tile_item=self.tile_item)
            self.main_window.undo_stack.push(cmd)

        if self.tile_item:
            self.tile_item.update()

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

    # --- Background Image ---

    def _pick_background_image(self):
        """Open a file dialog to select a background image for the tile."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if path:
            self._background_image_path = path
            self._update_bg_image_preview()

    def _clear_background_image(self):
        """Clear the tile's background image."""
        self._background_image_path = None
        self._update_bg_image_preview()

    def _update_bg_image_preview(self):
        """Update the background image preview label, respecting EXIF orientation."""
        if self._background_image_path:
            reader = QImageReader(self._background_image_path)
            reader.setAutoTransform(True)
            image = reader.read()
            if not image.isNull():
                pixmap = QPixmap.fromImage(image)
                self.bg_image_label.setPixmap(
                    pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                return
        self.bg_image_label.setText("No image")

    # --- Ambient Audio ---

    def _pick_ambient_audio(self):
        """Open a file dialog to select an ambient audio file for the tile."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Ambient Audio", "",
            "Audio (*.mp3 *.wav *.ogg *.flac *.m4a)"
        )
        if path:
            self._ambient_audio_path = path
            self.audio_path_label.setText(path)

    def _clear_ambient_audio(self):
        """Clear the tile's ambient audio."""
        self._ambient_audio_path = None
        self.audio_path_label.setText("")

    def _play_ambient_audio(self):
        """Play the tile's ambient audio file."""
        if self._ambient_audio_path:
            from core.audio_player import AudioPlayer
            AudioPlayer.instance().play(self._ambient_audio_path)

    def _stop_ambient_audio(self):
        """Stop any currently playing audio."""
        from core.audio_player import AudioPlayer
        AudioPlayer.instance().stop()

    def edit_triggers(self):
        """
        Open the trigger editor dialog for this tile.
        """
        dlg = TriggerEditorDialog(self.tile_data)
        dlg.exec_()

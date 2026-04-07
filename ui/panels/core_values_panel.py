from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox, QCheckBox,
    QLineEdit, QTextEdit, QPushButton, QGroupBox, QScrollArea,
    QHBoxLayout, QLabel, QFileDialog, QMessageBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPixmap, QImageReader
from models.tiles.tile_data import TileTag, TerrainType
from core.logger import app_logger


class CoreValuesPanel(QWidget):
    """
    Embedded panel that displays and edits the core attributes of a selected tile.

    Mirrors the fields from :class:`ui.dialogs.tile_dialog.TileDialog` but lives
    inside the main window's side panel instead of a separate dialog.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tile_data = None
        self._tile_item = None
        self._main_window = None
        self._original_state = None
        self._background_image_path = None
        self._ambient_audio_path = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction (widgets built once; values loaded per tile)
    # ------------------------------------------------------------------

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        container = QWidget()
        self.form = QFormLayout(container)
        self.form.setContentsMargins(8, 8, 8, 8)
        scroll.setWidget(container)

        # Read-only info
        self._id_label = QLabel()
        self._pos_label = QLabel()
        self.form.addRow("Tile ID:", self._id_label)
        self.form.addRow("Position:", self._pos_label)

        # Terrain
        self.terrain_input = QComboBox()
        self.terrain_input.addItems([t.name for t in TerrainType])
        self.form.addRow("Terrain:", self.terrain_input)

        # Tags
        self.tag_checkboxes = {}
        tag_group = QGroupBox("Tags")
        tag_layout = QVBoxLayout(tag_group)
        for tag in TileTag:
            cb = QCheckBox(tag.name.replace("_", " ").title())
            cb.setStyleSheet("""
                QCheckBox::indicator {
                    width: 16px; height: 16px;
                    border: 2px solid #888; border-radius: 3px;
                    background: transparent;
                }
                QCheckBox::indicator:checked {
                    background-color: #6d4c9e; border-color: #c084fc;
                }
            """)
            self.tag_checkboxes[tag] = cb
            tag_layout.addWidget(cb)
        self.form.addRow(tag_group)

        # Label / Zone / Note
        self.label_input = QLineEdit()
        self.form.addRow("User Label:", self.label_input)

        self.zone_id_input = QLineEdit()
        self.zone_id_input.setPlaceholderText("e.g. Guard Post, Main Hall")
        self.form.addRow("Encounter Zone:", self.zone_id_input)

        self.note_input = QTextEdit()
        self.note_input.setMaximumHeight(80)
        self.form.addRow("Note:", self.note_input)

        # Overlay color
        self.overlay_input = QLineEdit()
        color_btn = QPushButton("Pick Color")
        color_btn.clicked.connect(self._open_color_picker)
        color_row = QHBoxLayout()
        color_row.addWidget(self.overlay_input)
        color_row.addWidget(color_btn)
        self.form.addRow("Overlay Color:", color_row)

        # Background image
        self.bg_image_label = QLabel()
        self.bg_image_label.setFixedSize(80, 80)
        self.bg_image_label.setAlignment(Qt.AlignCenter)
        from core import theme_palette as tp
        self.bg_image_label.setStyleSheet(
            f"border: 1px solid {tp.get_themed('border_secondary')}; "
            f"background: {tp.get_themed('bg_secondary')};"
        )
        bg_btn = QPushButton("Choose Image...")
        bg_btn.clicked.connect(self._pick_bg_image)
        bg_clear_btn = QPushButton("Clear")
        bg_clear_btn.clicked.connect(self._clear_bg_image)
        bg_row = QHBoxLayout()
        bg_row.addWidget(self.bg_image_label)
        bg_btns = QVBoxLayout()
        bg_btns.addWidget(bg_btn)
        bg_btns.addWidget(bg_clear_btn)
        bg_row.addLayout(bg_btns)
        self.form.addRow("Background Image:", bg_row)

        # Ambient audio
        self.audio_label = QLineEdit()
        self.audio_label.setReadOnly(True)
        audio_btn = QPushButton("Choose...")
        audio_btn.clicked.connect(self._pick_audio)
        audio_clear_btn = QPushButton("Clear")
        audio_clear_btn.clicked.connect(self._clear_audio)
        audio_play_btn = QPushButton("Play")
        audio_play_btn.clicked.connect(self._play_audio)
        audio_stop_btn = QPushButton("Stop")
        audio_stop_btn.clicked.connect(self._stop_audio)
        audio_row = QHBoxLayout()
        for w in (self.audio_label, audio_btn, audio_clear_btn, audio_play_btn, audio_stop_btn):
            audio_row.addWidget(w)
        self.form.addRow("Ambient Audio:", audio_row)

        # Last updated
        self._updated_label = QLabel()
        self.form.addRow("Last Updated:", self._updated_label)

        # Save button
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        self.form.addRow(save_btn)

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def load(self, tile_data, tile_item, main_window):
        """Populate all widgets with the given tile's data."""
        self._tile_data = tile_data
        self._tile_item = tile_item
        self._main_window = main_window
        self._original_state = tile_data.to_dict()
        self._background_image_path = tile_data.background_image
        self._ambient_audio_path = tile_data.ambient_audio

        self._id_label.setText(tile_data.tile_id)
        self._pos_label.setText(str(tile_data.position))
        self.terrain_input.setCurrentText(tile_data.terrain.name)
        for tag, cb in self.tag_checkboxes.items():
            cb.setChecked(tag in tile_data.tags)
        self.label_input.setText(tile_data.user_label or "")
        self.zone_id_input.setText(tile_data.zone_id or "")
        self.note_input.setPlainText(tile_data.note or "")
        self.overlay_input.setText(tile_data.overlay_color or "#CCCCCC")
        self.audio_label.setText(tile_data.ambient_audio or "")
        self._updated_label.setText(tile_data.last_updated or "None")
        self._update_bg_preview()

    def save(self):
        """Write the form values back to tile_data and push an undo command."""
        if self._tile_data is None:
            return

        td = self._tile_data

        # START_ZONE exclusivity guard
        was_start = TileTag.START_ZONE.name in (self._original_state.get("tags") or [])
        will_be_start = self.tag_checkboxes[TileTag.START_ZONE].isChecked()
        if will_be_start and not was_start and self._tile_item:
            scene = self._tile_item.scene() if hasattr(self._tile_item, "scene") else None
            if scene:
                for item in scene.items():
                    if hasattr(item, "tile_data") and item is not self._tile_item:
                        if TileTag.START_ZONE in item.tile_data.tags:
                            QMessageBox.warning(
                                self, "Start Zone Conflict",
                                "Another tile is already marked as the Start Zone.\n"
                                "Only one Start Zone is allowed per scenario.\n\n"
                                "Remove the existing Start Zone tag first."
                            )
                            self.tag_checkboxes[TileTag.START_ZONE].setChecked(False)
                            return

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
        self._updated_label.setText(td.last_updated)

        new_state = td.to_dict()
        if self._main_window and hasattr(self._main_window, "undo_stack"):
            from ui.dialogs.tile_edit.tile_edit_command import TileEditCommand
            cmd = TileEditCommand(td, self._original_state, new_state, tile_item=self._tile_item)
            self._main_window.undo_stack.push(cmd)

        if self._tile_item:
            self._tile_item.update()

        self._original_state = new_state

        from core.gameCreation.event_bus import EventBus
        from core.events import TILE_MODIFIED
        EventBus.emit(TILE_MODIFIED, {"position": td.position, "tile_id": td.tile_id})

        app_logger.info(f"[CoreValuesPanel] Saved tile {td.tile_id}")

    # ------------------------------------------------------------------
    # Color picker
    # ------------------------------------------------------------------

    def _open_color_picker(self):
        from PyQt5.QtWidgets import QColorDialog
        initial = QColor(self.overlay_input.text() or "#CCCCCC")
        color = QColorDialog.getColor(initial, self, "Select Overlay Color")
        if color.isValid():
            self.overlay_input.setText(color.name())
            if self._tile_item:
                self._tile_item.set_overlay_color(color.name())

    # ------------------------------------------------------------------
    # Background image
    # ------------------------------------------------------------------

    def _pick_bg_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if path:
            self._background_image_path = path
            self._update_bg_preview()

    def _clear_bg_image(self):
        self._background_image_path = None
        self._update_bg_preview()

    def _update_bg_preview(self):
        if self._background_image_path:
            reader = QImageReader(self._background_image_path)
            reader.setAutoTransform(True)
            image = reader.read()
            if not image.isNull():
                pixmap = QPixmap.fromImage(image)
                self.bg_image_label.setPixmap(
                    pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                return
        self.bg_image_label.setText("No image")

    # ------------------------------------------------------------------
    # Ambient audio
    # ------------------------------------------------------------------

    def _pick_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Ambient Audio", "",
            "Audio (*.mp3 *.wav *.ogg *.flac *.m4a)"
        )
        if path:
            self._ambient_audio_path = path
            self.audio_label.setText(path)

    def _clear_audio(self):
        self._ambient_audio_path = None
        self.audio_label.setText("")

    def _play_audio(self):
        if self._ambient_audio_path:
            from core.audio_player import AudioPlayer
            AudioPlayer.instance().play(self._ambient_audio_path)

    def _stop_audio(self):
        from core.audio_player import AudioPlayer
        AudioPlayer.instance().stop()

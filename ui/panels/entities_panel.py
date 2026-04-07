import copy

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QListWidget, QListWidgetItem,
    QFormLayout, QLineEdit, QComboBox, QTextEdit,
    QLabel, QFileDialog, QMessageBox, QScrollArea,
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap
from models.entities.game_entity import GameEntity
from ui.panels.entity_list_item import EntityListItem
from core.logger import app_logger


class _EntityEditPanel(QWidget):
    """Right-side panel for editing a single entity's fields."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entity = None
        self._entity_index = -1
        self._tile_data = None
        self._side_panel = None
        self._dirty = False

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        self.form = QFormLayout(container)
        self.form.setContentsMargins(6, 6, 6, 6)
        scroll.setWidget(container)

        # Portrait
        self._image_path = None
        self.image_label = QLabel()
        self.image_label.setMinimumSize(80, 80)
        self.image_label.setMaximumSize(160, 160)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #ccc; background: #f5f5f5;")
        img_btn = QPushButton("Image...")
        img_btn.clicked.connect(self._pick_image)
        img_clear_btn = QPushButton("Clear")
        img_clear_btn.clicked.connect(self._clear_image)
        img_row = QHBoxLayout()
        img_row.addWidget(self.image_label)
        img_col = QVBoxLayout()
        img_col.addWidget(img_btn)
        img_col.addWidget(img_clear_btn)
        img_row.addLayout(img_col)
        self.form.addRow("Portrait:", img_row)

        self.name_input = QLineEdit()
        self.name_input.textChanged.connect(self._mark_dirty)
        self.form.addRow("Name:", self.name_input)

        self.type_input = QComboBox()
        self.type_input.addItems(["enemy", "npc", "player", "trap", "object"])
        self.type_input.currentTextChanged.connect(self._mark_dirty)
        self.form.addRow("Type:", self.type_input)

        self.inventory_box = QTextEdit()
        self.inventory_box.setMaximumHeight(70)
        self.inventory_box.setPlaceholderText("One item per line…")
        self.inventory_box.textChanged.connect(self._mark_dirty)
        self.form.addRow("Inventory:", self.inventory_box)

        # Voice settings
        from ui.voice.voice_settings_widget import VoiceSettingsWidget
        self._voice_widget = VoiceSettingsWidget()
        self._voice_widget.profile_changed.connect(self._mark_dirty)
        voice_toggle = QPushButton("Voice Settings")
        voice_toggle.setCheckable(True)
        voice_toggle.setStyleSheet("font-size: 11px; padding: 3px;")
        self._voice_widget.hide()
        voice_toggle.toggled.connect(self._voice_widget.setVisible)
        self.form.addRow(voice_toggle)
        self.form.addRow(self._voice_widget)

        # Action buttons
        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        stat_btn = QPushButton("Stat Block")
        stat_btn.clicked.connect(self._view_stat_block)
        self._trigger_btn = QPushButton("Triggers")
        self._trigger_btn.clicked.connect(self._open_triggers)
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._delete)
        for b in (save_btn, stat_btn, self._trigger_btn, delete_btn):
            btn_row.addWidget(b)
        self.form.addRow(btn_row)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------

    def load(self, entity, index, tile_data, side_panel):
        self._entity = entity
        self._entity_index = index
        self._tile_data = tile_data
        self._side_panel = side_panel
        self._dirty = False
        self._image_path = getattr(entity, "image_path", None)

        self.name_input.blockSignals(True)
        self.type_input.blockSignals(True)
        self.inventory_box.blockSignals(True)

        self.name_input.setText(entity.name)
        self.type_input.setCurrentText(entity.entity_type)
        self.inventory_box.setPlainText("\n".join(entity.inventory or []))

        self.name_input.blockSignals(False)
        self.type_input.blockSignals(False)
        self.inventory_box.blockSignals(False)

        self._update_image_preview()

        # Load voice profile if entity has one
        vp = getattr(entity, "voice_profile", None)
        if vp and hasattr(vp, "exaggeration"):
            self._voice_widget.set_profile(vp)
        # Set preview text from entity's first dialogue line
        dialogue = getattr(entity, "dialogue_lines", {})
        first_line = ""
        for lines in dialogue.values():
            if lines:
                first_line = lines[0]
                break
        self._voice_widget.set_preview_text(first_line or f"I am {entity.name}.")

        self.setVisible(True)

    def has_unsaved_changes(self) -> bool:
        return self._dirty

    # ------------------------------------------------------------------

    def _mark_dirty(self):
        self._dirty = True

    def _save(self):
        if self._entity is None:
            return
        self._entity.name = self.name_input.text()
        self._entity.entity_type = self.type_input.currentText()
        self._entity.inventory = self.inventory_box.toPlainText().splitlines()
        if self._image_path is not None:
            self._entity.image_path = self._image_path
        # Save voice profile
        self._entity.voice_profile = self._voice_widget.get_profile()
        self._dirty = False
        app_logger.info(f"[EntitiesPanel] Saved entity '{self._entity.name}'")

    def _delete(self):
        if self._entity is None or self._tile_data is None:
            return
        reply = QMessageBox.question(
            self, "Delete Entity",
            f"Delete '{self._entity.name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            if self._entity_index >= 0:
                self._tile_data.entities.pop(self._entity_index)
            self.setVisible(False)
            self._entity = None
            # Signal parent to refresh
            parent = self.parent()
            while parent:
                if hasattr(parent, "_refresh_list"):
                    parent._refresh_list()
                    break
                parent = parent.parent()

    def _view_stat_block(self):
        if self._entity is None:
            return
        from ui.dialogs.stat_block_dialog import StatBlockDialog
        dlg = StatBlockDialog(self._entity, parent=self)
        dlg.exec_()

    def _open_triggers(self):
        if self._entity is None or self._side_panel is None:
            return
        self._side_panel.open_trigger_panel_for_entity(self._entity)

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Portrait", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if path:
            self._image_path = path
            self._update_image_preview()
            self._mark_dirty()

    def _clear_image(self):
        self._image_path = None
        self._update_image_preview()
        self._mark_dirty()

    def _update_image_preview(self):
        if self._image_path:
            pixmap = QPixmap(self._image_path)
            if not pixmap.isNull():
                self.image_label.setPixmap(
                    pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                return
        self.image_label.setText("No image")


class EntitiesPanel(QWidget):
    """
    Embedded entity management panel.

    Left side: list of entities with ⋮ menus (edit / delete / duplicate).
    Right side: entity editor, shown when a entity is selected for editing.
    """

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._tile_data = None
        self._main_window = main_window
        self._side_panel = None

        splitter = QSplitter(Qt.Horizontal)

        # --- LEFT: entity list ---
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Entity")
        add_btn.clicked.connect(self._add_entity)
        import_btn = QPushButton("Import...")
        import_btn.clicked.connect(self._import_entity)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(import_btn)
        left_layout.addLayout(btn_row)

        self._list = QListWidget()
        self._list.setSpacing(2)
        left_layout.addWidget(self._list)

        splitter.addWidget(left)

        # --- RIGHT: entity editor ---
        self._editor = _EntityEditPanel(self)
        self._editor.setVisible(False)
        splitter.addWidget(self._editor)

        splitter.setSizes([200, 300])
        splitter.setCollapsible(1, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(splitter)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, tile_data, main_window, side_panel):
        """Populate the list from tile_data.entities."""
        self._tile_data = tile_data
        self._main_window = main_window
        self._side_panel = side_panel
        self._refresh_list()

    # ------------------------------------------------------------------
    # List management
    # ------------------------------------------------------------------

    def _refresh_list(self):
        self._list.clear()
        if self._tile_data is None:
            return
        for i, entity in enumerate(self._tile_data.entities):
            item = QListWidgetItem(self._list)
            item_widget = EntityListItem(entity)
            item_widget.edit_requested.connect(lambda e, idx=i: self._edit_entity(e, idx))
            item_widget.delete_requested.connect(self._delete_entity)
            item_widget.duplicate_requested.connect(self._duplicate_entity)
            item.setSizeHint(QSize(0, 36))
            self._list.addItem(item)
            self._list.setItemWidget(item, item_widget)

    def _guard_unsaved(self) -> bool:
        """Return True if it's safe to proceed (no unsaved changes or user dismissed)."""
        if self._editor.isVisible() and self._editor.has_unsaved_changes():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Discard them?",
                QMessageBox.Discard | QMessageBox.Cancel,
            )
            return reply == QMessageBox.Discard
        return True

    def _edit_entity(self, entity, index: int):
        if not self._guard_unsaved():
            return
        self._editor.load(entity, index, self._tile_data, self._side_panel)

    def _delete_entity(self, entity):
        if not self._guard_unsaved():
            return
        entity_name = entity.name
        try:
            self._tile_data.entities.remove(entity)
        except ValueError:
            pass
        self._editor.setVisible(False)
        self._refresh_list()

        from core.gameCreation.event_bus import EventBus
        from core.events import ENTITY_REMOVED
        EventBus.emit(ENTITY_REMOVED, {
            "position": self._tile_data.position if self._tile_data else None,
            "entity_name": entity_name,
        })

    def _duplicate_entity(self, entity):
        new_entity = copy.deepcopy(entity)
        new_entity.name = entity.name + " (copy)"
        self._tile_data.entities.append(new_entity)
        self._refresh_list()

    def _add_entity(self):
        if self._tile_data is None:
            return
        from ui.dialogs.new_entity_dialog import NewEntityDialog
        dlg = NewEntityDialog()
        if dlg.exec_():
            entity = dlg.get_entity()
            if entity:
                self._tile_data.entities.append(entity)
                self._refresh_list()

                from core.gameCreation.event_bus import EventBus
                from core.events import ENTITY_ADDED
                EventBus.emit(ENTITY_ADDED, {
                    "position": self._tile_data.position,
                    "entity_name": entity.name,
                })

    def _import_entity(self):
        if self._tile_data is None:
            return
        try:
            from ui.dialogs.universal_search_dialog import UniversalSearchDialog
            dlg = UniversalSearchDialog(mode="monster")
            if dlg.exec_():
                entity = dlg.get_selected_object()
                if entity:
                    self._tile_data.entities.append(entity)
                    self._refresh_list()

                    from core.gameCreation.event_bus import EventBus
                    from core.events import ENTITY_ADDED
                    EventBus.emit(ENTITY_ADDED, {
                        "position": self._tile_data.position,
                        "entity_name": entity.name,
                    })
        except Exception as e:
            app_logger.warning(f"[EntitiesPanel] Import failed: {e}")

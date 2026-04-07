"""DM dialog for creating/editing zones within a tile."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QListWidget, QListWidgetItem,
    QSpinBox, QCheckBox, QComboBox, QFormLayout, QSplitter,
    QWidget,
)
from PyQt5.QtCore import Qt, pyqtSignal

from models.tiles.tile_zone import TileZone, ZonePlacement


class ZoneEditorDialog(QDialog):
    """Dialog for creating/editing zones within a tile.

    Signals:
        zones_saved(list): Updated list of TileZone on save.
    """

    zones_saved = pyqtSignal(list)

    def __init__(self, tile_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Zones: {getattr(tile_data, 'user_label', '') or 'Tile'}")
        self.resize(700, 500)

        self._tile_data = tile_data
        self._zones = [self._copy_zone(z) for z in getattr(tile_data, "zones", [])]
        self._current_index = -1

        layout = QHBoxLayout(self)

        # Left: zone list
        left = QVBoxLayout()
        self._zone_list = QListWidget()
        self._zone_list.currentRowChanged.connect(self._on_zone_selected)
        left.addWidget(QLabel("Zones:"))
        left.addWidget(self._zone_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add")
        add_btn.clicked.connect(self._add_zone)
        btn_row.addWidget(add_btn)
        remove_btn = QPushButton("- Remove")
        remove_btn.clicked.connect(self._remove_zone)
        btn_row.addWidget(remove_btn)
        left.addLayout(btn_row)
        layout.addLayout(left, stretch=1)

        # Right: zone details
        right = QVBoxLayout()
        form = QFormLayout()

        self._name_input = QLineEdit()
        form.addRow("Name:", self._name_input)

        self._desc_input = QTextEdit()
        self._desc_input.setMaximumHeight(80)
        form.addRow("Description:", self._desc_input)

        self._tags_input = QLineEdit()
        self._tags_input.setPlaceholderText("indoor, tavern, dark")
        form.addRow("Tags:", self._tags_input)

        right.addLayout(form)

        # Connections
        right.addWidget(QLabel("Connections:"))
        self._conn_layout = QVBoxLayout()
        right.addLayout(self._conn_layout)

        # Actions
        action_row = QHBoxLayout()
        action_row.addStretch()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save)
        action_row.addWidget(save_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        action_row.addWidget(cancel_btn)
        right.addLayout(action_row)
        layout.addLayout(right, stretch=2)

        self._rebuild_list()

    def _copy_zone(self, zone):
        return TileZone.from_dict(zone.to_dict())

    def _rebuild_list(self):
        self._zone_list.clear()
        for z in self._zones:
            self._zone_list.addItem(z.label)

    def _on_zone_selected(self, index):
        if 0 <= index < len(self._zones):
            self._current_index = index
            z = self._zones[index]
            self._name_input.setText(z.label)
            self._desc_input.setPlainText(z.description or "")
            self._tags_input.setText(", ".join(z.tags))
            self._rebuild_connections(z)
        else:
            self._current_index = -1

    def _rebuild_connections(self, zone):
        while self._conn_layout.count():
            item = self._conn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for z in self._zones:
            if z.zone_id == zone.zone_id:
                continue
            cb = QCheckBox(z.label)
            cb.setChecked(z.zone_id in zone.connections)
            cb.setProperty("zone_id", z.zone_id)
            self._conn_layout.addWidget(cb)

    def _add_zone(self):
        import uuid
        zid = f"zone_{uuid.uuid4().hex[:6]}"
        new_zone = TileZone(zone_id=zid, label=f"New Zone {len(self._zones) + 1}")
        self._zones.append(new_zone)
        self._rebuild_list()
        self._zone_list.setCurrentRow(len(self._zones) - 1)

    def _remove_zone(self):
        if self._current_index >= 0:
            del self._zones[self._current_index]
            self._current_index = -1
            self._rebuild_list()

    def _on_save(self):
        # Apply current edits to the active zone
        if 0 <= self._current_index < len(self._zones):
            z = self._zones[self._current_index]
            z.label = self._name_input.text()
            z.description = self._desc_input.toPlainText()
            z.tags = [t.strip() for t in self._tags_input.text().split(",") if t.strip()]

            # Update connections from checkboxes
            conns = []
            for i in range(self._conn_layout.count()):
                w = self._conn_layout.itemAt(i).widget()
                if isinstance(w, QCheckBox) and w.isChecked():
                    conns.append(w.property("zone_id"))
            z.connections = conns

        self.zones_saved.emit(self._zones)
        self.accept()

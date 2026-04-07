"""Dockable entity palette for drag-and-drop placement on the map."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton,
)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QByteArray
from PyQt5.QtGui import QDrag


# Quick template entity data
QUICK_TEMPLATES = [
    {"name": "Guard", "entity_type": "npc", "stats": {"hp": 11, "max_hp": 11, "Dexterity": 12}, "tags": []},
    {"name": "Merchant", "entity_type": "npc", "stats": {"hp": 9, "max_hp": 9, "Dexterity": 10}, "tags": ["merchant"]},
    {"name": "Commoner", "entity_type": "npc", "stats": {"hp": 4, "max_hp": 4, "Dexterity": 10}, "tags": []},
    {"name": "Noble", "entity_type": "npc", "stats": {"hp": 9, "max_hp": 9, "Dexterity": 12}, "tags": []},
]

MIME_TYPE = "application/x-dnd-entity"


class EntityPalettePanel(QWidget):
    """Dockable palette for dragging entities onto the map.

    Signals:
        entity_dropped_on_tile(dict, int, int): Entity data, col, row.
    """

    entity_dropped_on_tile = pyqtSignal(dict, int, int)

    def __init__(self, scenario_entities: list | None = None, parent=None):
        super().__init__(parent)
        self._scenario_entities = scenario_entities or []
        self._srd_creatures: list[dict] | None = None  # lazy loaded

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Search
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search entities...")
        self._search.textChanged.connect(self._on_search)
        layout.addWidget(self._search)

        # Quick templates
        layout.addWidget(QLabel("Quick Templates:"))
        self._template_list = QListWidget()
        self._template_list.setDragEnabled(True)
        self._template_list.setMaximumHeight(100)
        for tmpl in QUICK_TEMPLATES:
            item = QListWidgetItem(tmpl["name"])
            item.setData(Qt.UserRole, json.dumps(tmpl))
            self._template_list.addItem(item)
        self._template_list.startDrag = lambda actions: self._start_drag(self._template_list)
        layout.addWidget(self._template_list)

        # SRD Creatures
        layout.addWidget(QLabel("SRD Creatures:"))
        self._srd_list = QListWidget()
        self._srd_list.setDragEnabled(True)
        self._srd_list.startDrag = lambda actions: self._start_drag(self._srd_list)
        layout.addWidget(self._srd_list)

        load_btn = QPushButton("Load SRD Creatures")
        load_btn.clicked.connect(self._load_srd_creatures)
        layout.addWidget(load_btn)

        # Scenario NPCs
        layout.addWidget(QLabel("Scenario NPCs:"))
        self._scenario_list = QListWidget()
        self._scenario_list.setDragEnabled(True)
        self._scenario_list.startDrag = lambda actions: self._start_drag(self._scenario_list)
        self._rebuild_scenario_list()
        layout.addWidget(self._scenario_list)

    def refresh_scenario_entities(self, entities: list) -> None:
        self._scenario_entities = entities
        self._rebuild_scenario_list()

    def _rebuild_scenario_list(self) -> None:
        self._scenario_list.clear()
        for entity in self._scenario_entities:
            name = getattr(entity, "name", str(entity))
            data = entity.to_dict() if hasattr(entity, "to_dict") else {"name": name, "entity_type": "npc"}
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, json.dumps(data))
            self._scenario_list.addItem(item)

    def _load_srd_creatures(self) -> None:
        if self._srd_creatures is not None:
            return  # already loaded
        self._srd_creatures = []
        srd_path = Path("core/data_/rulebook_json/5e-SRD-Monsters.json")
        if not srd_path.exists():
            self._srd_list.addItem("SRD data not found")
            return

        try:
            import json as json_mod
            with open(srd_path, "r", encoding="utf-8") as f:
                monsters = json_mod.load(f)
            for m in monsters[:100]:  # limit for performance
                name = m.get("name", "Unknown")
                cr = m.get("challenge_rating", "?")
                hp = m.get("hit_points", 10)
                data = {
                    "name": name,
                    "entity_type": "enemy",
                    "stats": {"hp": hp, "max_hp": hp, "Dexterity": 10},
                }
                item = QListWidgetItem(f"{name} (CR {cr})")
                item.setData(Qt.UserRole, json.dumps(data))
                self._srd_list.addItem(item)
                self._srd_creatures.append(data)
        except Exception:
            self._srd_list.addItem("Failed to load SRD data")

    def _start_drag(self, list_widget: QListWidget) -> None:
        item = list_widget.currentItem()
        if not item:
            return

        entity_json = item.data(Qt.UserRole)
        if not entity_json:
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(MIME_TYPE, QByteArray(entity_json.encode()))
        drag.setMimeData(mime)
        drag.exec_(Qt.CopyAction)

    def _on_search(self, text: str) -> None:
        text_lower = text.lower()
        for list_widget in (self._template_list, self._srd_list, self._scenario_list):
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                item.setHidden(text_lower not in item.text().lower())

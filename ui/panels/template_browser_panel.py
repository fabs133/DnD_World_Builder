"""Dockable template browser for reusable entity and zone templates."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QTabBar,
)
from PyQt5.QtCore import Qt, pyqtSignal


class TemplateBrowserPanel(QWidget):
    """Panel for browsing and applying entity/zone templates.

    Signals:
        entity_template_applied(dict): Entity dict ready for tile placement.
        zone_template_applied(list): List of zone dicts to apply.
    """

    entity_template_applied = pyqtSignal(dict)
    zone_template_applied = pyqtSignal(list)

    _TAB_ENTITIES = 0
    _TAB_ZONES = 1
    _TAB_MY_TEMPLATES = 2

    def __init__(self, registry=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._registry = registry
        self._build_ui()
        if registry:
            self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Search
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search templates...")
        self._search.textChanged.connect(self._on_search)
        layout.addWidget(self._search)

        # Tabs
        self._tabs = QTabBar()
        self._tabs.addTab("Entities")
        self._tabs.addTab("Zones")
        self._tabs.addTab("My Templates")
        self._tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tabs)

        # Template list
        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list)

        # Detail label
        self._detail = QLabel("")
        self._detail.setWordWrap(True)
        self._detail.setStyleSheet("color: gray; font-size: 11px;")
        self._detail.setMaximumHeight(60)
        layout.addWidget(self._detail)

        # Apply button
        btn_row = QHBoxLayout()
        self._apply_btn = QPushButton("Apply to Selected Tile")
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._on_apply)
        btn_row.addWidget(self._apply_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_registry(self, registry) -> None:
        self._registry = registry
        self.refresh()

    def refresh(self) -> None:
        self._on_tab_changed(self._tabs.currentIndex())

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_tab_changed(self, index: int) -> None:
        self._list.clear()
        self._detail.clear()
        self._apply_btn.setEnabled(False)

        if not self._registry:
            return

        if index == self._TAB_ENTITIES:
            for tmpl in self._registry.get_entity_templates():
                item = QListWidgetItem(f"{tmpl.name}  [{tmpl.category}]")
                item.setData(Qt.UserRole, ("entity", tmpl.template_id))
                item.setToolTip(tmpl.description)
                self._list.addItem(item)

        elif index == self._TAB_ZONES:
            for tmpl in self._registry.get_zone_templates():
                zones_count = len(tmpl.zones_data)
                item = QListWidgetItem(f"{tmpl.name}  ({zones_count} zones)")
                item.setData(Qt.UserRole, ("zone", tmpl.template_id))
                item.setToolTip(tmpl.description)
                self._list.addItem(item)

        elif index == self._TAB_MY_TEMPLATES:
            for tmpl in self._registry.get_entity_templates():
                if not tmpl.is_builtin:
                    item = QListWidgetItem(f"{tmpl.name}  [entity]")
                    item.setData(Qt.UserRole, ("entity", tmpl.template_id))
                    self._list.addItem(item)
            for tmpl in self._registry.get_zone_templates():
                if not tmpl.is_builtin:
                    item = QListWidgetItem(f"{tmpl.name}  [zone]")
                    item.setData(Qt.UserRole, ("zone", tmpl.template_id))
                    self._list.addItem(item)

        self._apply_filters()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self._apply_btn.setEnabled(True)
        data = item.data(Qt.UserRole)
        if not data:
            return

        tmpl_type, tmpl_id = data
        if tmpl_type == "entity":
            for t in self._registry.get_entity_templates():
                if t.template_id == tmpl_id:
                    self._detail.setText(f"{t.description}\nTags: {', '.join(t.tags)}")
                    break
        elif tmpl_type == "zone":
            for t in self._registry.get_zone_templates():
                if t.template_id == tmpl_id:
                    self._detail.setText(f"{t.description}\nTags: {', '.join(t.tags)}")
                    break

    def _on_apply(self) -> None:
        item = self._list.currentItem()
        if not item:
            return

        data = item.data(Qt.UserRole)
        if not data:
            return

        tmpl_type, tmpl_id = data
        if tmpl_type == "entity":
            for t in self._registry.get_entity_templates():
                if t.template_id == tmpl_id:
                    self.entity_template_applied.emit(t.to_entity_dict())
                    break
        elif tmpl_type == "zone":
            for t in self._registry.get_zone_templates():
                if t.template_id == tmpl_id:
                    self.zone_template_applied.emit(t.to_zones_dicts())
                    break

    def _on_search(self, text: str) -> None:
        self._apply_filters()

    def _apply_filters(self) -> None:
        query = self._search.text().lower()
        for i in range(self._list.count()):
            item = self._list.item(i)
            match = not query or query in item.text().lower()
            item.setHidden(not match)

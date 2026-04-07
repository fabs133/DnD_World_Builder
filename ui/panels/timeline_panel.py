"""Dockable story timeline panel for DM session planning and navigation."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QTextEdit, QMenu, QAbstractItemView,
    QInputDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal


class TimelinePanel(QWidget):
    """DM story timeline showing scenes linked to map tiles.

    Signals:
        navigate_to_tile(str): Emitted with tile_id when user double-clicks a scene.
        timeline_modified(): Emitted on any structural change (add/remove/reorder/edit).
    """

    navigate_to_tile = pyqtSignal(str)
    timeline_modified = pyqtSignal()

    _STATUS_ICONS = {
        "planned": "\u25cb",    # ○
        "active": "\u25cf",     # ●
        "completed": "\u2713",  # ✓
        "skipped": "\u2298",    # ⊘
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._timeline = None  # StoryTimeline instance
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Button row
        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Scene")
        add_btn.clicked.connect(self._add_scene)
        btn_row.addWidget(add_btn)

        autogen_btn = QPushButton("Auto-generate")
        autogen_btn.setToolTip("Create scenes from labeled tiles on the map")
        autogen_btn.clicked.connect(self._auto_generate_stub)
        btn_row.addWidget(autogen_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Scene list with drag reordering
        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.InternalMove)
        self._list.setDefaultDropAction(Qt.MoveAction)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        self._list.model().rowsMoved.connect(self._on_rows_moved)
        layout.addWidget(self._list)

        # Notes editor (for selected scene)
        layout.addWidget(QLabel("Scene Notes:"))
        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(100)
        self._notes_edit.setPlaceholderText("DM notes for the selected scene...")
        self._notes_edit.textChanged.connect(self._on_notes_changed)
        layout.addWidget(self._notes_edit)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_timeline(self, timeline) -> None:
        """Load a StoryTimeline and rebuild the display."""
        self._timeline = timeline
        self._rebuild_list()

    def get_timeline(self):
        """Return the current StoryTimeline for saving."""
        return self._timeline

    def auto_generate(self, tiles: list) -> None:
        """Create scenes from labeled tiles, ordered by position."""
        if not self._timeline:
            return
        # Sort tiles by (row, col)
        labeled = [(t["tile_id"], t.get("user_label", ""), t.get("position", [0, 0]))
                    for t in tiles if t.get("user_label")]
        labeled.sort(key=lambda x: (x[2][0], x[2][1]))

        for tile_id, label, _pos in labeled:
            # Skip if scene already exists for this tile
            existing = any(tile_id in s.tile_ids for s in self._timeline.scenes)
            if not existing:
                self._timeline.add_scene(title=label, tile_ids=[tile_id])

        self._rebuild_list()
        self.timeline_modified.emit()

    # ------------------------------------------------------------------
    # List management
    # ------------------------------------------------------------------

    def _rebuild_list(self) -> None:
        self._list.clear()
        self._notes_edit.clear()
        if not self._timeline:
            return

        for scene in sorted(self._timeline.scenes, key=lambda s: s.order):
            icon = self._STATUS_ICONS.get(scene.status, "?")
            tiles_str = ", ".join(scene.tile_ids) if scene.tile_ids else "no tile"
            act_prefix = f"[{scene.act}] " if scene.act else ""
            text = f"{icon}  {act_prefix}{scene.title}  ({tiles_str})"

            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, scene.scene_id)
            item.setToolTip(scene.description or scene.notes or "")
            self._list.addItem(item)

    def _selected_scene_id(self) -> str | None:
        item = self._list.currentItem()
        if item:
            return item.data(Qt.UserRole)
        return None

    def _find_scene(self, scene_id: str):
        if not self._timeline:
            return None
        for s in self._timeline.scenes:
            if s.scene_id == scene_id:
                return s
        return None

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        scene_id = item.data(Qt.UserRole)
        scene = self._find_scene(scene_id)
        if scene:
            self._notes_edit.blockSignals(True)
            self._notes_edit.setPlainText(scene.notes)
            self._notes_edit.blockSignals(False)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        scene_id = item.data(Qt.UserRole)
        scene = self._find_scene(scene_id)
        if scene and scene.tile_ids:
            self.navigate_to_tile.emit(scene.tile_ids[0])

    def _on_notes_changed(self) -> None:
        scene_id = self._selected_scene_id()
        if scene_id:
            scene = self._find_scene(scene_id)
            if scene:
                scene.notes = self._notes_edit.toPlainText()
                self.timeline_modified.emit()

    def _on_rows_moved(self, *_args) -> None:
        if not self._timeline:
            return
        for i in range(self._list.count()):
            item = self._list.item(i)
            scene_id = item.data(Qt.UserRole)
            scene = self._find_scene(scene_id)
            if scene:
                scene.order = i
        self.timeline_modified.emit()

    def _add_scene(self) -> None:
        if not self._timeline:
            return
        title, ok = QInputDialog.getText(self, "Add Scene", "Scene title:")
        if ok and title.strip():
            self._timeline.add_scene(title=title.strip())
            self._rebuild_list()
            self.timeline_modified.emit()

    def _auto_generate_stub(self) -> None:
        """Stub — MainWindow connects this to provide tile data."""
        pass

    def _show_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if not item:
            return
        scene_id = item.data(Qt.UserRole)

        menu = QMenu(self)
        menu.addAction("Mark Active", lambda: self._set_status(scene_id, "active"))
        menu.addAction("Mark Completed", lambda: self._set_status(scene_id, "completed"))
        menu.addAction("Mark Skipped", lambda: self._set_status(scene_id, "skipped"))
        menu.addSeparator()
        menu.addAction("Delete", lambda: self._delete_scene(scene_id))
        menu.exec_(self._list.mapToGlobal(pos))

    def _set_status(self, scene_id: str, status: str) -> None:
        if not self._timeline:
            return
        if status == "active":
            self._timeline.mark_active(scene_id)
        elif status == "completed":
            self._timeline.mark_completed(scene_id)
        else:
            scene = self._find_scene(scene_id)
            if scene:
                scene.status = status
        self._rebuild_list()
        self.timeline_modified.emit()

    def _delete_scene(self, scene_id: str) -> None:
        if not self._timeline:
            return
        self._timeline.remove_scene(scene_id)
        self._rebuild_list()
        self.timeline_modified.emit()

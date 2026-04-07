"""Dockable asset manager for batch importing and assigning media files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QFileDialog,
    QTabBar, QStackedWidget,
)
from PyQt5.QtCore import Qt, pyqtSignal, QByteArray, QSize, QMimeData
from PyQt5.QtGui import QDrag, QIcon, QPixmap

from core.media_manager import MediaManager

ASSET_MIME_TYPE = "application/x-dnd-asset"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg"}
ALL_EXTENSIONS = IMAGE_EXTENSIONS | AUDIO_EXTENSIONS

_IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
_AUDIO_FILTER = "Audio (*.wav *.mp3 *.ogg)"
_ALL_FILTER = f"Media ({' '.join('*' + e for e in sorted(ALL_EXTENSIONS))})"


class AssetManagerPanel(QWidget):
    """Dockable panel for batch managing scenario media assets.

    Signals:
        asset_assigned(str, str): (asset_relative_path, tile_id).
    """

    asset_assigned = pyqtSignal(str, str)

    # Tab indices
    _TAB_ALL = 0
    _TAB_IMAGES = 1
    _TAB_AUDIO = 2

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._media_manager: Optional[MediaManager] = None
        self._all_assets: list[dict] = []  # {"path": str, "type": "image"|"audio"}
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Search bar + import button
        top_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search assets...")
        self._search.textChanged.connect(self._apply_filters)
        top_row.addWidget(self._search)

        import_btn = QPushButton("Import...")
        import_btn.setToolTip("Import image or audio files into the workspace")
        import_btn.clicked.connect(self.import_files)
        top_row.addWidget(import_btn)
        layout.addLayout(top_row)

        # Category tabs
        self._tabs = QTabBar()
        self._tabs.addTab("All")
        self._tabs.addTab("Images")
        self._tabs.addTab("Audio")
        self._tabs.currentChanged.connect(self._apply_filters)
        layout.addWidget(self._tabs)

        # Asset grid (icon mode list widget)
        self._list = QListWidget()
        self._list.setViewMode(QListWidget.IconMode)
        self._list.setIconSize(QSize(80, 80))
        self._list.setResizeMode(QListWidget.Adjust)
        self._list.setSpacing(6)
        self._list.setDragEnabled(True)
        self._list.startDrag = lambda actions: self._start_drag()
        layout.addWidget(self._list)

        # Status label
        self._status = QLabel("No workspace loaded")
        self._status.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self._status)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_workspace(self, workspace_path) -> None:
        """Set the workspace and scan for existing media files."""
        self._media_manager = MediaManager(workspace_path)
        self.refresh()

    def refresh(self) -> None:
        """Rescan the media directory and rebuild the asset list."""
        self._all_assets.clear()
        if not self._media_manager:
            self._rebuild_list()
            return

        for rel_path in self._media_manager.list_images():
            self._all_assets.append({"path": rel_path, "type": "image"})
        for rel_path in self._media_manager.list_audio():
            self._all_assets.append({"path": rel_path, "type": "audio"})

        self._rebuild_list()

    def import_files(self) -> int:
        """Open a multi-file dialog and import selected files.

        :return: Number of files imported.
        :rtype: int
        """
        if not self._media_manager:
            return 0

        paths, _ = QFileDialog.getOpenFileNames(
            self, "Import Media Files", "",
            f"{_ALL_FILTER};;{_IMAGE_FILTER};;{_AUDIO_FILTER}")
        if not paths:
            return 0

        count = 0
        for path_str in paths:
            p = Path(path_str)
            ext = p.suffix.lower()
            if ext in IMAGE_EXTENSIONS:
                self._media_manager.import_image(path_str)
                count += 1
            elif ext in AUDIO_EXTENSIONS:
                self._media_manager.import_audio(path_str)
                count += 1

        if count:
            self.refresh()
        return count

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def _apply_filters(self, *_args) -> None:
        search_text = self._search.text().lower()
        tab = self._tabs.currentIndex()

        for i in range(self._list.count()):
            item = self._list.item(i)
            data = json.loads(item.data(Qt.UserRole))
            asset_type = data.get("type", "")
            filename = Path(data["path"]).name.lower()

            type_match = (
                tab == self._TAB_ALL
                or (tab == self._TAB_IMAGES and asset_type == "image")
                or (tab == self._TAB_AUDIO and asset_type == "audio")
            )
            search_match = not search_text or search_text in filename
            item.setHidden(not (type_match and search_match))

        self._update_status()

    # ------------------------------------------------------------------
    # Drag support
    # ------------------------------------------------------------------

    def _start_drag(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        payload = item.data(Qt.UserRole)
        if not payload:
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(ASSET_MIME_TYPE, QByteArray(payload.encode()))
        drag.setMimeData(mime)

        # Set drag pixmap from item icon
        icon = item.icon()
        if not icon.isNull():
            drag.setPixmap(icon.pixmap(48, 48))

        drag.exec_(Qt.CopyAction)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rebuild_list(self) -> None:
        self._list.clear()
        for asset in self._all_assets:
            rel_path = asset["path"]
            filename = Path(rel_path).name
            payload = json.dumps(asset)

            item = QListWidgetItem(filename)
            item.setData(Qt.UserRole, payload)
            item.setToolTip(rel_path)

            if asset["type"] == "image" and self._media_manager:
                abs_path = self._media_manager.resolve_path(rel_path)
                if abs_path.exists():
                    pixmap = QPixmap(str(abs_path))
                    if not pixmap.isNull():
                        thumb = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        item.setIcon(QIcon(thumb))

            self._list.addItem(item)

        self._apply_filters()

    def _update_status(self) -> None:
        total = len(self._all_assets)
        visible = sum(1 for i in range(self._list.count()) if not self._list.item(i).isHidden())
        images = sum(1 for a in self._all_assets if a["type"] == "image")
        audio = sum(1 for a in self._all_assets if a["type"] == "audio")
        self._status.setText(f"{total} assets ({images} images, {audio} audio) — {visible} shown")

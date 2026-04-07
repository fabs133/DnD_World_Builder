"""Scenario picker dialog — lets the user choose a scenario from workspace/."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class ScenarioPickerDialog(QDialog):
    """Modal dialog that scans workspace/ for scenarios and lets the user pick one."""

    def __init__(self, workspace_dir: Path = Path("workspace"), parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._workspace = workspace_dir
        self._selected_path: Path | None = None
        self._scenarios: list[dict] = []

        self.setWindowTitle("Select Scenario")
        self.setMinimumSize(420, 360)
        self._build_ui()
        self._scan_scenarios()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QLabel("Choose a scenario to play:")
        header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setFont(QFont("Consolas", 10))
        self._list.itemDoubleClicked.connect(self._on_select)
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        select_btn = QPushButton("Play")
        select_btn.setDefault(True)
        select_btn.setStyleSheet(
            "QPushButton { background: #1a472a; color: white; font-weight: bold; "
            "padding: 8px 20px; } QPushButton:hover { background: #22c55e; }"
        )
        select_btn.clicked.connect(self._on_select)
        btn_row.addWidget(select_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)

    def _scan_scenarios(self) -> None:
        """Find all workspace subdirectories containing a map.json."""
        if not self._workspace.is_dir():
            return

        for child in sorted(self._workspace.iterdir()):
            map_file = child / "map.json"
            if not map_file.is_file():
                continue

            meta = self._read_meta(map_file)
            self._scenarios.append({
                "path": map_file,
                "folder": child.name,
                "meta": meta,
            })

            map_name = meta.get("map_name", child.name)
            grid_type = meta.get("grid_type", "?")
            rows = meta.get("rows", "?")
            cols = meta.get("cols", "?")
            label = f"{map_name}  ({grid_type} {cols}x{rows})  [{child.name}]"

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, len(self._scenarios) - 1)
            self._list.addItem(item)

        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    @staticmethod
    def _read_meta(map_path: Path) -> dict:
        try:
            with open(map_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("meta", {})
        except Exception:
            return {}

    def _on_select(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        idx = item.data(Qt.UserRole)
        self._selected_path = self._scenarios[idx]["path"]
        self._selected_meta = self._scenarios[idx]["meta"]
        self.accept()

    def selected_map_path(self) -> Path | None:
        return self._selected_path

    def selected_meta(self) -> dict:
        return getattr(self, "_selected_meta", {})

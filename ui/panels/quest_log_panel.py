"""Quest Log Panel — track active, available, and completed quests."""

from __future__ import annotations

from typing import Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor


_TYPE_COLORS = {
    "world": "#d4a030",
    "main": "#c05030",
    "side": "#3080c0",
}


class QuestLogPanel(QWidget):
    """Displays quests grouped by status: Active / Available / Completed.

    Signals:
        navigate_to_quest(str): quest_id — navigate to quest giver on map.
    """

    navigate_to_quest = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._quests: list[dict] = []
        self._active: set[str] = set()
        self._completed: set[str] = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Filter buttons
        filter_row = QHBoxLayout()
        self._filter_btns = {}
        for label, key in [("All", "all"), ("Active", "active"),
                           ("Available", "available"), ("Completed", "completed")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(key == "all")
            btn.setStyleSheet(
                "QPushButton { padding: 2px 6px; font-size: 11px; border-radius: 3px; }"
                "QPushButton:checked { background: #4a4a5a; color: white; }"
            )
            btn.clicked.connect(lambda _, k=key: self._set_filter(k))
            filter_row.addWidget(btn)
            self._filter_btns[key] = btn
        layout.addLayout(filter_row)

        # Quest list
        self._quest_list = QListWidget()
        self._quest_list.setStyleSheet(
            "QListWidget { background: #2a2a2a; border: 1px solid #444; }"
            "QListWidget::item { padding: 4px 6px; border-bottom: 1px solid #333; }"
            "QListWidget::item:selected { background: #3a3a4a; }"
        )
        self._quest_list.itemClicked.connect(self._on_quest_clicked)
        layout.addWidget(self._quest_list, stretch=1)

        # Detail area
        self._detail = QTextEdit()
        self._detail.setReadOnly(True)
        self._detail.setMaximumHeight(150)
        self._detail.setStyleSheet(
            "QTextEdit { background: #252520; border: 1px solid #444; "
            "color: #d4c8a0; font-size: 11px; padding: 4px; }")
        self._detail.setPlaceholderText("Select a quest to see details...")
        layout.addWidget(self._detail)

        # Action buttons
        btn_row = QHBoxLayout()
        self._accept_btn = QPushButton("Accept Quest")
        self._accept_btn.clicked.connect(self._accept_quest)
        btn_row.addWidget(self._accept_btn)
        self._locate_btn = QPushButton("Find on Map")
        self._locate_btn.clicked.connect(self._locate_quest)
        btn_row.addWidget(self._locate_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._current_filter = "all"
        self._selected_quest: dict | None = None

    def load_quests(self, quests: list[dict]) -> None:
        """Load quest data from map.json."""
        self._quests = quests
        self._refresh()

    def set_active(self, quest_ids: set[str]) -> None:
        self._active = quest_ids
        self._refresh()

    def set_completed(self, quest_ids: set[str]) -> None:
        self._completed = quest_ids
        self._refresh()

    def _get_status(self, quest: dict) -> str:
        qid = quest.get("id", "")
        if qid in self._completed:
            return "completed"
        if qid in self._active:
            return "active"
        return "available"

    def _set_filter(self, key: str) -> None:
        for k, btn in self._filter_btns.items():
            btn.setChecked(k == key)
        self._current_filter = key
        self._refresh()

    def _refresh(self) -> None:
        self._quest_list.clear()
        for quest in self._quests:
            status = self._get_status(quest)
            if self._current_filter != "all" and status != self._current_filter:
                continue

            name = quest.get("name", "?")
            qtype = quest.get("type", "side")
            giver = quest.get("giver", "")
            difficulty = quest.get("difficulty", 1)

            color = _TYPE_COLORS.get(qtype, "#888")
            status_icon = {"active": "[*]", "completed": "[x]", "available": "[ ]"}.get(status, "[ ]")

            display = f"{status_icon} {name}  ({qtype})  D:{difficulty}"
            if giver:
                display += f"  - {giver}"

            item = QListWidgetItem(display)
            item.setForeground(QColor(color))
            item.setData(Qt.UserRole, quest)
            self._quest_list.addItem(item)

    def _on_quest_clicked(self, item: QListWidgetItem) -> None:
        quest = item.data(Qt.UserRole)
        if not quest:
            return
        self._selected_quest = quest
        status = self._get_status(quest)

        html = f"<b style='font-size:13px;'>{quest.get('name', '?')}</b><br>"
        html += f"<i>Type: {quest.get('type', 'side')} | Difficulty: {quest.get('difficulty', 1)}</i><br>"
        if quest.get("giver"):
            html += f"<b>Quest Giver:</b> {quest['giver']}<br>"
        html += f"<br>{quest.get('description', '')}<br>"

        objectives = quest.get("objectives", [])
        if objectives:
            html += "<br><b>Objectives:</b><ul>"
            for obj in objectives:
                html += f"<li>{obj}</li>"
            html += "</ul>"

        reward = quest.get("reward", {})
        if reward:
            parts = []
            if reward.get("xp"):
                parts.append(f"{reward['xp']} XP")
            if reward.get("items"):
                parts.append(", ".join(reward["items"]))
            if parts:
                html += f"<br><b>Reward:</b> {' + '.join(parts)}"

        html += f"<br><i>Status: {status}</i>"
        self._detail.setHtml(html)
        self._accept_btn.setEnabled(status == "available")
        self._accept_btn.setText("Accept Quest" if status == "available" else
                                  "Complete Quest" if status == "active" else
                                  "Completed")

    def _accept_quest(self) -> None:
        if not self._selected_quest:
            return
        qid = self._selected_quest.get("id", "")
        status = self._get_status(self._selected_quest)
        if status == "available":
            self._active.add(qid)
        elif status == "active":
            self._active.discard(qid)
            self._completed.add(qid)
        self._refresh()

    def _locate_quest(self) -> None:
        if self._selected_quest:
            self.navigate_to_quest.emit(self._selected_quest.get("id", ""))

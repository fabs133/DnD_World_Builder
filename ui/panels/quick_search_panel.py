"""Quick Access Search panel — global entity/tile search with slash commands."""

from __future__ import annotations

from typing import Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QFrame,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor

from ui.panels.search_index import SearchIndex, SearchResultItem
from ui.panels.slash_commands import SlashCommandEngine


# ─── Category colors ────────────────────────────────────────────────

_TYPE_COLORS = {
    "player": "#3a64c8", "enemy": "#c83a3a", "npc": "#3ac878",
    "ally": "#3ac860", "companion": "#3ac860", "monster": "#c83a3a",
    "hostile": "#c83a3a", "object": "#b4a028", "trap": "#c87828",
    "spawn": "#3a64c8", "location": "#888888",
}

_TYPE_DOT_COLORS = {
    "player": QColor(60, 100, 200), "enemy": QColor(200, 60, 60),
    "npc": QColor(60, 200, 120), "ally": QColor(60, 200, 100),
    "object": QColor(180, 160, 40), "location": QColor(140, 140, 140),
    "trap": QColor(200, 120, 40), "spawn": QColor(60, 100, 200),
}


class QuickSearchPanel(QWidget):
    """Searchable, filterable panel for finding entities and tiles globally.

    Signals:
        navigate_to_tile(str): tile_id to pan the map to.
    """

    navigate_to_tile = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._main_window = None
        self._index = SearchIndex()
        self._commands = SlashCommandEngine()
        self._active_categories: set[str] | None = None  # None = all
        self._active_subcategories: set[str] | None = None

        self.setMinimumWidth(300)
        self._build_ui()
        self._register_commands()

        # Debounce timer
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(150)
        self._debounce.timeout.connect(self._do_search)

    def set_main_window(self, mw) -> None:
        self._main_window = mw

    # ─── UI Construction ────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Search bar
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search or type / for commands...")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(self._on_text_changed)
        self._search_input.returnPressed.connect(self._on_return)
        layout.addWidget(self._search_input)

        # Category filter buttons
        filter_row = QHBoxLayout()
        filter_row.setSpacing(2)
        self._filter_btns: dict[str, QPushButton] = {}
        for label, key in [("All", "all"), ("Entities", "entity"),
                           ("Objects", "object"), ("Tiles", "tile")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(key == "all")
            btn.setStyleSheet(
                "QPushButton { padding: 3px 8px; font-size: 11px; border-radius: 3px; }"
                "QPushButton:checked { background: #4a4a5a; color: white; }"
            )
            btn.clicked.connect(lambda checked, k=key: self._on_filter(k))
            filter_row.addWidget(btn)
            self._filter_btns[key] = btn
        layout.addLayout(filter_row)

        # Entity sub-filter row (visible when "Entities" active)
        self._sub_filter_row = QHBoxLayout()
        self._sub_filter_row.setSpacing(2)
        self._sub_btns: dict[str, QPushButton] = {}
        for label, key in [("Enemy", "enemy"), ("NPC", "npc"),
                           ("Player", "player"), ("Ally", "ally")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(
                "QPushButton { padding: 2px 6px; font-size: 10px; border-radius: 2px; }"
                "QPushButton:checked { background: #5a5a6a; color: white; }"
            )
            btn.clicked.connect(self._on_sub_filter_changed)
            self._sub_filter_row.addWidget(btn)
            self._sub_btns[key] = btn
        self._sub_filter_container = QWidget()
        self._sub_filter_container.setLayout(self._sub_filter_row)
        self._sub_filter_container.hide()
        layout.addWidget(self._sub_filter_container)

        # Status line
        self._status = QLabel("")
        self._status.setStyleSheet("color: #888; font-size: 11px; padding: 2px;")
        layout.addWidget(self._status)

        # Results list
        self._results_list = QListWidget()
        self._results_list.setStyleSheet(
            "QListWidget { background: #2a2a2a; border: 1px solid #444; }"
            "QListWidget::item { padding: 4px 6px; border-bottom: 1px solid #333; }"
            "QListWidget::item:selected { background: #3a3a4a; }"
            "QListWidget::item:hover { background: #333340; }"
        )
        self._results_list.itemClicked.connect(self._on_result_clicked)
        self._results_list.itemDoubleClicked.connect(self._on_result_double_clicked)
        layout.addWidget(self._results_list, stretch=1)

        # Command completions (shown over results when in / mode)
        self._cmd_list = QListWidget()
        self._cmd_list.setStyleSheet(
            "QListWidget { background: #1a1a2a; border: 1px solid #556; }"
            "QListWidget::item { padding: 3px 6px; color: #aaf; }"
            "QListWidget::item:selected { background: #2a2a4a; }"
        )
        self._cmd_list.setMaximumHeight(150)
        self._cmd_list.hide()
        self._cmd_list.itemClicked.connect(self._on_cmd_clicked)
        layout.addWidget(self._cmd_list)

    # ─── Filter Logic ───────────────────────────────────────────

    def _on_filter(self, key: str) -> None:
        # Uncheck all, check the clicked one
        for k, btn in self._filter_btns.items():
            btn.setChecked(k == key)

        if key == "all":
            self._active_categories = None
            self._sub_filter_container.hide()
        elif key == "entity":
            self._active_categories = {"entity"}
            self._sub_filter_container.show()
        elif key == "object":
            self._active_categories = {"object"}
            self._sub_filter_container.hide()
        elif key == "tile":
            self._active_categories = {"tile"}
            self._sub_filter_container.hide()

        self._active_subcategories = None
        self._on_sub_filter_changed()
        self._do_search()

    def _on_sub_filter_changed(self) -> None:
        checked = [k for k, btn in self._sub_btns.items() if btn.isChecked()]
        self._active_subcategories = set(checked) if checked else None
        self._do_search()

    # ─── Search Logic ───────────────────────────────────────────

    def _on_text_changed(self, text: str) -> None:
        if text.startswith("/"):
            self._show_command_completions(text)
            self._results_list.hide()
            self._cmd_list.show()
        else:
            self._cmd_list.hide()
            self._results_list.show()
            self._debounce.start()
            # Hint: if first word matches a command, show hint in status
            first_word = text.split()[0].lower() if text.strip().split() else ""
            if first_word in self._commands.commands:
                cmd = self._commands.commands[first_word]
                self._status.setText(f"Tip: press Enter to run as /{cmd.name} {cmd.arg_hint}")
                self._status.setStyleSheet("color: #88a; font-size: 11px; padding: 2px;")

    def _on_return(self) -> None:
        text = self._search_input.text().strip()
        if not text:
            return
        # Auto-add / prefix if user typed a known command without it
        if not text.startswith("/"):
            first_word = text.split()[0].lower() if text.split() else ""
            if first_word in self._commands.commands:
                text = "/" + text
        if text.startswith("/"):
            # Execute command
            self._cmd_list.hide()
            self._results_list.show()
            result = self._commands.execute(text)
            msg = result or "Done."
            self._status.setText(f"> {msg}")
            self._status.setStyleSheet(
                "color: #8af; font-size: 12px; padding: 4px; "
                "font-weight: bold; background: #2a2a3a; border-radius: 3px;")
            self._search_input.clear()
            # Reset status style after 4 seconds
            QTimer.singleShot(4000, lambda: self._status.setStyleSheet(
                "color: #888; font-size: 11px; padding: 2px; background: none;"))
        else:
            # On enter with regular text, navigate to first result
            if self._results_list.count() > 0:
                self._on_result_clicked(self._results_list.item(0))

    def _do_search(self) -> None:
        query = self._search_input.text().strip()
        if query.startswith("/"):
            return

        results = self._index.search(
            query,
            categories=self._active_categories,
            subcategories=self._active_subcategories,
        )

        self._results_list.clear()
        for r in results[:200]:  # cap at 200 results
            badge = r.entity_type_str or r.subcategory
            pos_str = f"({r.tile_position[0]}, {r.tile_position[1]})"
            display = f"{r.name}  [{badge}]  {pos_str}"

            item = QListWidgetItem(display)
            color = _TYPE_DOT_COLORS.get(r.subcategory, QColor(140, 140, 140))
            item.setForeground(color)
            item.setData(Qt.UserRole, r)
            self._results_list.addItem(item)

        count = len(results)
        shown = min(count, 200)
        self._status.setText(
            f"{count} result{'s' if count != 1 else ''}"
            + (f" (showing {shown})" if count > 200 else "")
        )

    # ─── Navigation ─────────────────────────────────────────────

    def _on_result_clicked(self, item: QListWidgetItem) -> None:
        result: SearchResultItem = item.data(Qt.UserRole)
        if not result:
            return
        self._navigate_to(result)

    def _on_result_double_clicked(self, item: QListWidgetItem) -> None:
        result: SearchResultItem = item.data(Qt.UserRole)
        if not result:
            return
        self._navigate_to(result)
        # Also select the tile in the side panel
        if self._main_window and result.source_tile_item:
            self._main_window.select_tile(result.source_tile_item)

    def _navigate_to(self, result: SearchResultItem) -> None:
        tile_item = result.source_tile_item
        if tile_item and self._main_window:
            self._main_window.view.smooth_center_on(
                tile_item.x(), tile_item.y())
            self._main_window.select_tile(tile_item)

    # ─── Slash Commands ─────────────────────────────────────────

    def _register_commands(self) -> None:
        self._commands.register(
            "goto", "Pan map to tile at row,col", self._cmd_goto, "row,col")
        self._commands.register(
            "find", "Search for text", self._cmd_find, "<text>")
        self._commands.register(
            "count", "Count entities of type", self._cmd_count, "<type>")
        self._commands.register(
            "select", "Find and select entity", self._cmd_select, "<name>")

    def _cmd_goto(self, args: str) -> str | None:
        parts = args.replace(",", " ").split()
        if len(parts) < 2:
            return "Usage: /goto row,col  (e.g. /goto 10 10)"
        try:
            row, col = int(parts[0]), int(parts[1])
        except ValueError:
            return "Invalid coordinates — use numbers like: /goto 10 10"
        if self._main_window:
            # Find the tile and navigate
            for item in self._main_window.scene.items():
                td = getattr(item, "tile_data", None)
                if td and getattr(td, "tile_id", "") == f"{row}_{col}":
                    self._main_window.view.smooth_center_on(item.x(), item.y())
                    self._main_window.select_tile(item)
                    return f"Jumped to ({row}, {col})"
            return f"No tile found at ({row}, {col})"
        return "No editor window"

    def _cmd_find(self, args: str) -> str | None:
        self._search_input.setText(args)
        return None

    def _cmd_count(self, args: str) -> str | None:
        t = args.strip().lower()
        if not t:
            return f"Total indexed: {self._index.total()}"
        count = self._index.count_by_type(t)
        return f"{t}: {count} found"

    def _cmd_select(self, args: str) -> str | None:
        results = self._index.search(args.strip())
        if results:
            self._navigate_to(results[0])
            return f"Selected: {results[0].name} at {results[0].tile_position}"
        return f"Not found: {args}"

    def _show_command_completions(self, text: str) -> None:
        self._cmd_list.clear()
        completions = self._commands.get_completions(text[1:])  # strip /
        for cmd in completions:
            hint = f" {cmd.arg_hint}" if cmd.arg_hint else ""
            item = QListWidgetItem(f"/{cmd.name}{hint}  —  {cmd.description}")
            item.setData(Qt.UserRole, cmd.name)
            self._cmd_list.addItem(item)

    def _on_cmd_clicked(self, item: QListWidgetItem) -> None:
        cmd_name = item.data(Qt.UserRole)
        if cmd_name:
            self._search_input.setText(f"/{cmd_name} ")
            self._search_input.setFocus()

    # ─── Refresh ────────────────────────────────────────────────

    def refresh(self) -> None:
        """Rebuild the search index from the current scene."""
        if self._main_window and hasattr(self._main_window, "scene"):
            self._index.build(self._main_window.scene.items())
            self._do_search()

"""Dialog to generate per-tile background images via ComfyUI.

Presents a simple form with:
- Tile count (auto-detected from current map)
- Biome hint text field
- Start / Cancel buttons
- Progress bar and status label

Generation runs in a background QThread so the UI stays responsive.
On completion, tile background images are written back to the tile
items in the scene so the canvas updates immediately.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QProgressBar, QWidget, QMessageBox,
)

from core.logger import app_logger
from tools.tile_background_generator import (
    generate_tile_backgrounds,
    map_slug,
)


# Rough average per tile (ComfyUI submission + polling + copy).
_SECONDS_PER_TILE_ESTIMATE = 35


# ── Worker thread ──────────────────────────────────────────────────────


class _GenWorker(QThread):
    progress = pyqtSignal(int, int, str)  # done, total, status
    finished_ok = pyqtSignal(dict)        # {(x, y): rel_path}
    failed = pyqtSignal(str)

    def __init__(
        self,
        tile_dicts: list[dict],
        map_name: str,
        biome_hint: str,
        parent=None,
    ):
        super().__init__(parent)
        self._tile_dicts = tile_dicts
        self._map_name = map_name
        self._biome_hint = biome_hint
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:
        try:
            results = generate_tile_backgrounds(
                tiles=self._tile_dicts,
                map_name=self._map_name,
                on_progress=lambda done, total, status: self.progress.emit(
                    done, total, status
                ),
                cancel_check=lambda: self._cancel_requested,
                biome_hint=self._biome_hint,
            )
            self.finished_ok.emit(results)
        except Exception as exc:
            app_logger.error(f"[TileBgGen] Worker failed: {exc}")
            self.failed.emit(str(exc))


# ── Dialog ─────────────────────────────────────────────────────────────


class TileBackgroundGenDialog(QDialog):
    """Modal dialog that drives per-tile background generation."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self._main_window = main_window
        self._worker: _GenWorker | None = None

        # Collect tile items from the scene up front.
        from models.tiles.square_tile_item import SquareTileItem
        try:
            from models.tiles.hex_tile_item import HexTileItem
        except ImportError:
            HexTileItem = None  # type: ignore

        tile_classes: tuple = (SquareTileItem,)
        if HexTileItem is not None:
            tile_classes = (SquareTileItem, HexTileItem)

        self._tile_items = [
            item for item in main_window.scene.items()
            if isinstance(item, tile_classes)
        ]
        # Keep a mapping from (x, y) → tile item so we can update back.
        self._items_by_pos: dict[tuple[int, int], Any] = {}
        for item in self._tile_items:
            pos = getattr(item.tile_data, "position", None)
            if pos is not None:
                self._items_by_pos[(int(pos[0]), int(pos[1]))] = item

        self._tile_dicts = [item.tile_data.to_dict() for item in self._tile_items]

        # Derive the map name / slug from the current_map_path.
        current_path = getattr(main_window, "current_map_path", None)
        if current_path:
            self._map_name = Path(current_path).stem
        else:
            self._map_name = "untitled_map"

        self.setWindowTitle("Generate Tile Backgrounds")
        self.setMinimumWidth(420)
        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        count = len(self._tile_dicts)
        est_seconds = count * _SECONDS_PER_TILE_ESTIMATE
        est_minutes = max(1, est_seconds // 60)

        layout.addWidget(QLabel(
            f"<b>Map:</b> {self._map_name} ({map_slug(self._map_name)})"))
        layout.addWidget(QLabel(f"<b>Target:</b> {count} tiles"))
        layout.addWidget(QLabel(
            f"<b>Estimated time:</b> ~{est_minutes} minutes "
            f"(at ~{_SECONDS_PER_TILE_ESTIMATE}s per tile)"))

        layout.addWidget(QLabel("Existing files are skipped, so you can "
                                "cancel and resume later."))

        # Biome hint
        hint_row = QHBoxLayout()
        hint_row.addWidget(QLabel("Biome hint (optional):"))
        self._biome_input = QLineEdit()
        self._biome_input.setPlaceholderText("e.g. dark fantasy forest")
        hint_row.addWidget(self._biome_input, stretch=1)
        layout.addLayout(hint_row)

        # Progress
        self._progress = QProgressBar()
        self._progress.setRange(0, max(1, count))
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        self._status = QLabel("Ready.")
        self._status.setStyleSheet("color: #888; font-size: 10px;")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._start_btn = QPushButton("Start")
        self._start_btn.setDefault(True)
        self._start_btn.clicked.connect(self._on_start)
        btn_row.addWidget(self._start_btn)

        self._cancel_btn = QPushButton("Close")
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._cancel_btn)
        layout.addLayout(btn_row)

        # Guard: zero tiles.
        if count == 0:
            self._start_btn.setEnabled(False)
            self._status.setText("No tiles in the current map.")

    # ── Actions ────────────────────────────────────────────────────

    def _on_start(self) -> None:
        if self._worker and self._worker.isRunning():
            return

        confirm = QMessageBox.question(
            self,
            "Start Generation",
            f"Generate backgrounds for {len(self._tile_dicts)} tiles via "
            f"ComfyUI?\n\nEnsure ComfyUI is running on the configured API "
            f"endpoint.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if confirm != QMessageBox.Yes:
            return

        self._start_btn.setEnabled(False)
        self._cancel_btn.setText("Cancel")
        self._progress.setValue(0)
        self._status.setText("Starting…")

        self._worker = _GenWorker(
            tile_dicts=self._tile_dicts,
            map_name=self._map_name,
            biome_hint=self._biome_input.text().strip(),
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_cancel(self) -> None:
        if self._worker and self._worker.isRunning():
            # Running → request cancel, keep dialog open until thread exits.
            self._worker.request_cancel()
            self._status.setText("Cancelling… completed tiles will be kept.")
            self._cancel_btn.setEnabled(False)
        else:
            self.reject()

    # ── Worker signal handlers ─────────────────────────────────────

    def _on_progress(self, done: int, total: int, status: str) -> None:
        self._progress.setRange(0, max(1, total))
        self._progress.setValue(done)
        self._status.setText(status)

    def _on_finished(self, results: dict) -> None:
        # Write paths back to the tile items and refresh their images.
        updated = 0
        for (x, y), rel_path in results.items():
            item = self._items_by_pos.get((x, y))
            if item is None:
                continue
            item.tile_data.background_image = rel_path
            if hasattr(item, "reload_background_image"):
                try:
                    item.reload_background_image()
                except Exception as exc:
                    app_logger.warning(
                        f"[TileBgGen] reload_background_image failed for "
                        f"({x}, {y}): {exc}"
                    )
            updated += 1

        self._status.setText(
            f"Done. Updated {updated} tile(s). "
            f"Save the map to persist the new backgrounds."
        )
        self._start_btn.setEnabled(False)
        self._cancel_btn.setText("Close")
        self._cancel_btn.setEnabled(True)

    def _on_failed(self, message: str) -> None:
        self._status.setText(f"Error: {message}")
        self._start_btn.setEnabled(True)
        self._cancel_btn.setText("Close")
        self._cancel_btn.setEnabled(True)

    # ── Dialog lifecycle ───────────────────────────────────────────

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.request_cancel()
            self._worker.wait(5000)
        super().closeEvent(event)

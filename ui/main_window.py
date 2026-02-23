from PyQt5.QtWidgets import (
    QMainWindow, QGraphicsScene, QVBoxLayout, QHBoxLayout,
    QPushButton, QWidget, QAction, QFileDialog, QLabel, QSplitter,
    QDockWidget,
)
from PyQt5.QtCore import Qt, QPointF, QTimer
from PyQt5.QtWidgets import QUndoStack
import json
import math
from datetime import datetime
from pathlib import Path

from models.tiles.tile_data import TileData
from models.tiles.square_tile_item import SquareTileItem
from models.tiles.hex_tile_item import HexTileItem
from core.backup_manager import BackupManager
from core.logger import app_logger
from ui.map_view import MapView


def hex_tile_center(row, col, hex_size):
    """Calculate the pixel center of a flat-top hex tile at a given grid position."""
    horiz = 1.5 * hex_size
    vert = math.sqrt(3) * hex_size
    x = col * horiz
    y = row * vert + (col % 2) * (vert / 2)
    return x, y


class MainWindow(QMainWindow):
    """
    Main application window for the DnD Map Editor.

    The window is split horizontally: the map canvas on the left and
    TileSidePanel on the right. Selecting a tile (left-click) populates
    the side panel with that tile's data.
    """

    def __init__(self, settings, grid_type="square", rows=None, cols=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = settings
        self.setWindowTitle("DnD Map Editor")
        self.grid_type = grid_type
        self.selected_tile = None
        self.backup_manager = BackupManager()
        self.undo_stack = QUndoStack(self)
        self.current_map_path = None

        # Color mode state (replaces paint_mode_active / active_tile_preset)
        self.color_mode_active = False
        self.active_color = "#CCCCCC"

        # Multiplayer session
        self.session_manager = None

        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.timeout.connect(self._auto_save)
        self._init_auto_save()

        self.init_ui()
        self.init_menu()

        if rows is not None and cols is not None:
            self.init_grid(rows, cols)

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def init_ui(self):
        """Build the main layout: map (left) + side panel (right) in a QSplitter."""
        self.view = MapView()
        self.scene = QGraphicsScene(self)
        self.view.setScene(self.scene)

        # --- Map container (left column) ---
        map_container = QWidget()
        map_layout = QVBoxLayout(map_container)
        map_layout.setContentsMargins(0, 0, 0, 0)
        map_layout.setSpacing(0)
        map_layout.addWidget(self.view)

        # Persistent hint label below the canvas
        hint = QLabel(
            "Tip: Right-click any tile to edit its attributes  \u00b7  "
            "Enable Paint Mode then Left-click to paint"
        )
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("font-size: 11px; color: gray; padding: 2px;")
        map_layout.addWidget(hint)

        # Color mode indicator bar (shown when color mode is on)
        self.color_bar = QLabel(
            "  Color Mode — left-click to paint  |  right-click to sample  "
        )
        self.color_bar.setAlignment(Qt.AlignCenter)
        self.color_bar.setStyleSheet(
            "border: 2px solid #22c55e; color: #22c55e; font-size: 11px; padding: 2px;"
        )
        self.color_bar.hide()
        map_layout.addWidget(self.color_bar)

        # Compact toolbar: save buttons only
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(4, 2, 4, 2)
        toolbar_layout.addWidget(self.create_button("Save Scenario", self.save_scenario))
        toolbar_layout.addWidget(self.create_button("Save Map", self.save_map_dialog))
        map_layout.addWidget(toolbar)

        # --- Side panel (right column) ---
        from ui.panels.tile_side_panel import TileSidePanel
        self.side_panel = TileSidePanel(self)
        self.side_panel.setMinimumWidth(360)

        # --- Horizontal splitter ---
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(map_container)
        splitter.addWidget(self.side_panel)
        splitter.setSizes([700, 380])
        splitter.setCollapsible(0, False)

        self.setCentralWidget(splitter)

        # --- Session panel dock (hidden until session starts) ---
        from network.ui.session_panel import SessionPanel
        self.session_panel = SessionPanel()
        self.session_panel.disconnect_requested.connect(self._disconnect_session)
        self._session_dock = QDockWidget("Session", self)
        self._session_dock.setWidget(self.session_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self._session_dock)
        self._session_dock.hide()

        # --- Initiative tracker dock (hidden until combat starts) ---
        from ui.panels.initiative_panel import InitiativePanel
        self.initiative_panel = InitiativePanel()
        self._initiative_dock = QDockWidget("Initiative", self)
        self._initiative_dock.setWidget(self.initiative_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self._initiative_dock)
        self._initiative_dock.hide()

        self.statusBar().showMessage(
            "Right-click a tile to edit attributes  |  Ctrl+Z Undo  |  Ctrl+Y Redo"
        )

    def init_menu(self):
        """Build the menu bar."""
        menubar = self.menuBar()
        edit_menu = menubar.addMenu("Edit")

        undo_action = self.undo_stack.createUndoAction(self, "&Undo")
        undo_action.setShortcut("Ctrl+Z")
        edit_menu.addAction(undo_action)

        redo_action = self.undo_stack.createRedoAction(self, "&Redo")
        redo_action.setShortcut("Ctrl+Y")
        edit_menu.addAction(redo_action)

        view_menu = menubar.addMenu("View")
        reset_zoom_action = QAction("Reset &Zoom", self)
        reset_zoom_action.setShortcut("Ctrl+0")
        reset_zoom_action.triggered.connect(self.view.reset_zoom)
        view_menu.addAction(reset_zoom_action)

        initiative_toggle = self._initiative_dock.toggleViewAction()
        initiative_toggle.setText("&Initiative Tracker")
        initiative_toggle.setShortcut("Ctrl+I")
        view_menu.addAction(initiative_toggle)

        # --- Session menu ---
        session_menu = menubar.addMenu("Session")

        host_action = QAction("&Host Session...", self)
        host_action.triggered.connect(self._host_session)
        session_menu.addAction(host_action)

        join_action = QAction("&Join Session...", self)
        join_action.triggered.connect(self._join_session)
        session_menu.addAction(join_action)

        session_menu.addSeparator()

        self._disconnect_action = QAction("&Disconnect", self)
        self._disconnect_action.triggered.connect(self._disconnect_session)
        self._disconnect_action.setEnabled(False)
        session_menu.addAction(self._disconnect_action)

        help_menu = menubar.addMenu("Help")
        tutorial_action = QAction("Tutorial", self)
        tutorial_action.triggered.connect(self._show_tutorial)
        help_menu.addAction(tutorial_action)

    def _show_tutorial(self):
        from ui.dialogs.tutorial_dialog import TutorialDialog
        TutorialDialog(self.settings, self).exec_()

    # ------------------------------------------------------------------
    # Grid management
    # ------------------------------------------------------------------

    def init_grid(self, rows, cols):
        if self.grid_type == "square":
            self.create_square_grid(rows, cols, 50)
        elif self.grid_type == "hex":
            self.create_hex_grid(rows, cols, 30)
        else:
            raise ValueError("Unsupported grid type. Use 'square' or 'hex'.")

    def create_square_grid(self, rows, cols, size):
        for i in range(rows):
            for j in range(cols):
                tile_id = f"{i}_{j}"
                tile_data = TileData(tile_id=tile_id, position=(i, j))
                tile = SquareTileItem(j * size, i * size, size, tile_data, self)
                tile_data.tile_item = tile
                self.scene.addItem(tile)

    def create_hex_grid(self, rows, cols, hex_size):
        for row in range(rows):
            for col in range(cols):
                x, y = hex_tile_center(row, col, hex_size)
                center = QPointF(x, y)
                tile_id = f"{row}_{col}"
                tile_data = TileData(tile_id=tile_id, position=(row, col))
                tile = HexTileItem(center, hex_size, tile_data, self)
                tile_data.tile_item = tile
                self.scene.addItem(tile)

    def initialize_default_map(self):
        """Initialize a new default map using grid settings."""
        self.scene.clear()
        self.grid_type = self.settings.get("grid_type", "square")
        rows = self.settings.get("default_rows", 15)
        cols = self.settings.get("default_cols", 15)
        self.init_grid(rows, cols)
        app_logger.info(f"[Grid Initialized] {self.grid_type} {rows}x{cols}")

    # ------------------------------------------------------------------
    # Tile selection
    # ------------------------------------------------------------------

    def select_tile(self, tile_item):
        """Called by tile items on click; loads the tile into the side panel."""
        if self.color_mode_active:
            return  # color mode overrides normal selection
        self.selected_tile = tile_item
        self.side_panel.load_tile(tile_item.tile_data, tile_item, self)

    # ------------------------------------------------------------------
    # Color mode
    # ------------------------------------------------------------------

    def activate_color_mode(self, color: str):
        """Enable color-painting mode with the given hex color."""
        self.color_mode_active = True
        self.active_color = color
        self.color_bar.show()
        self.scene.update()

    def deactivate_color_mode(self):
        """Disable color-painting mode."""
        self.color_mode_active = False
        self.color_bar.hide()
        self.scene.update()

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def save_map_dialog(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Map", "", "JSON Files (*.json)")
        if path:
            self.current_map_path = path
            self.save_map_to_file(path)

    def save_map_to_file(self, filename="map.json"):
        map_path = Path(filename)
        should_backup = map_path.exists()

        tile_data_list = [
            item.tile_data.to_dict()
            for item in self.scene.items()
            if isinstance(item, (SquareTileItem, HexTileItem))
        ]

        full_map_data = {
            "version": "1.0",
            "meta": {"author": "Fabio", "created": datetime.now().isoformat()},
            "tiles": tile_data_list,
        }

        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(full_map_data, f, indent=2)

        app_logger.info(f"[Saved] Map written to {map_path}")

        if should_backup:
            self.backup_manager.backup_map(map_path)

    def save_scenario(self):
        from core.export_manager import ExportManager

        final_path_str, _ = QFileDialog.getSaveFileName(
            self, "Save Scenario As", "", "Scenario Bundle (*.zip)"
        )
        if not final_path_str:
            return

        final_path = Path(final_path_str)
        should_backup = final_path.exists()

        temp_map_path = Path("temp_map.json")
        self.save_map_to_file(temp_map_path)

        profile_dir = Path("profiles") if Path("profiles").exists() else None
        media_dir = Path("media") if Path("media").exists() else None

        export_manager = ExportManager(export_dir=final_path.parent)
        bundle_path = export_manager.export_bundle(temp_map_path, profile_dir, media_dir)

        bundle_path.rename(final_path)
        temp_map_path.unlink()

        app_logger.info(f"[Exported] Scenario exported to {final_path}")

        if should_backup:
            self.backup_manager.backup_map(final_path)

    def load_map_from_file(self, filename):
        self.current_map_path = filename
        self.scene.clear()

        try:
            with open(filename, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as e:
            app_logger.error(f"[Load Error] Could not read file: {e}")
            return

        version = raw_data.get("version", "unknown")
        app_logger.info(f"[Loading Map] Version: {version}, Meta: {raw_data.get('meta', {})}")

        meta = raw_data.get("meta", {})
        self.grid_type = meta.get("grid_type", "square")

        tiles = raw_data.get("tiles", [])
        if not tiles:
            rows = meta.get("rows", 25)
            cols = meta.get("cols", 25)
            self.init_grid(rows, cols)
            app_logger.info(f"[Grid Initialized] Empty map loaded with {rows}x{cols}")
            return

        for td_data in tiles:
            tile_data = TileData.from_dict(td_data)
            row, col = tile_data.position

            if self.grid_type == "square":
                size = 50
                x, y = col * size, row * size
                tile = SquareTileItem(x, y, size, tile_data, self)
            elif self.grid_type == "hex":
                hex_size = 30
                x, y = hex_tile_center(row, col, hex_size)
                center = QPointF(x, y)
                tile = HexTileItem(center, hex_size, tile_data, self)
            else:
                raise ValueError(f"Unsupported grid type: {self.grid_type}")

            tile_data.tile_item = tile
            self.scene.addItem(tile)

        app_logger.info(f"[Loaded] {len(tiles)} tiles loaded from {filename}")

    # ------------------------------------------------------------------
    # Auto-save
    # ------------------------------------------------------------------

    def _init_auto_save(self):
        enabled = self.settings.get("auto_save_enabled", True)
        interval = self.settings.get("auto_save_interval_seconds", 300)
        if enabled and interval > 0:
            self._auto_save_timer.start(interval * 1000)
            app_logger.debug(f"[AutoSave] Enabled with {interval}s interval")
        else:
            self._auto_save_timer.stop()
            app_logger.debug("[AutoSave] Disabled")

    def _auto_save(self):
        if self.current_map_path:
            self.save_map_to_file(self.current_map_path)
            app_logger.info(f"[AutoSave] Saved to {self.current_map_path}")

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def create_button(self, text, callback, checkable=False, enabled=True):
        button = QPushButton(text)
        button.setCheckable(checkable)
        button.setEnabled(enabled)
        button.clicked.connect(callback)
        return button

    # ------------------------------------------------------------------
    # Multiplayer session
    # ------------------------------------------------------------------

    def _host_session(self):
        from network.ui.host_dialog import HostDialog
        dlg = HostDialog(self.settings, self)
        if dlg.exec_():
            self._start_hosting(dlg.port)

    def _join_session(self):
        from network.ui.join_dialog import JoinDialog
        dlg = JoinDialog(self.settings, self)
        if dlg.exec_():
            self._start_joining(dlg.host, dlg.port, dlg.player_name)

    def _start_hosting(self, port):
        from network.session_manager import SessionManager

        gm = self._build_gamemaster_from_scene()
        self.session_manager = SessionManager(gamemaster=gm, settings=self.settings)
        self.session_manager.signals.chat_received.connect(self.session_panel.append_chat)
        self.session_manager.signals.disconnected.connect(self._on_session_ended)
        self.session_panel.chat_submitted.connect(self._on_chat_submitted)
        self.session_manager.host(port)

        self.session_panel.set_hosting(
            self.session_manager.join_address or f"localhost:{port}"
        )
        self._session_dock.show()
        self._disconnect_action.setEnabled(True)
        self.statusBar().showMessage(f"Hosting session on port {port}")

    def _start_joining(self, host_addr, port, player_name):
        from network.session_manager import SessionManager

        self.session_manager = SessionManager(settings=self.settings)
        self.session_manager.signals.connected.connect(
            lambda: self.session_panel.set_connected(host_addr)
        )
        self.session_manager.signals.chat_received.connect(self.session_panel.append_chat)
        self.session_manager.signals.entity_claimed.connect(self.session_panel.set_entity_claim)
        self.session_manager.signals.disconnected.connect(self._on_session_ended)
        self.session_manager.signals.connection_error.connect(
            lambda e: self.statusBar().showMessage(f"Connection error: {e}")
        )
        self.session_panel.chat_submitted.connect(self._on_chat_submitted)
        self.session_manager.join(host_addr, port, player_name)

        self._session_dock.show()
        self._disconnect_action.setEnabled(True)
        self.statusBar().showMessage(f"Connecting to {host_addr}:{port}...")

        # Save last host for convenience
        if self.settings:
            self.settings.set("multiplayer_last_host", host_addr)
            self.settings.set("multiplayer_player_name", player_name)

    def _disconnect_session(self):
        if self.session_manager:
            if self.session_manager.is_hosting:
                self.session_manager.stop_hosting()
            else:
                self.session_manager.leave()
            self.session_manager = None
        self._on_session_ended()

    def _on_session_ended(self):
        self._disconnect_action.setEnabled(False)
        self._session_dock.hide()
        self.session_panel.clear()
        self.statusBar().showMessage("Session ended")

    def _on_chat_submitted(self, message):
        if self.session_manager:
            self.session_manager.send_chat(message)

    def _build_gamemaster_from_scene(self):
        """Create a Gamemaster populated from the current scene."""
        from models.game_master import Gamemaster
        from models.world.world import World
        from models.world.world_tile_manager import WorldTileManager

        gm = Gamemaster()

        tile_manager = WorldTileManager(0, 0, self.grid_type)
        for item in self.scene.items():
            if hasattr(item, "tile_data"):
                td = item.tile_data
                tile_manager.tiles[td.position] = td
                for entity in td.entities:
                    tile_manager.entities.setdefault(td.position, []).append(entity)
                    gm.add_entity(entity)

        gm.world = World(
            world_version="1.0",
            width=self.settings.get("default_cols", 25),
            height=self.settings.get("default_rows", 25),
            tile_type=self.grid_type,
        )
        gm.world.tile_manager = tile_manager

        return gm

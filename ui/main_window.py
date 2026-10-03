import json
import math
import random
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QObject, QPointF, Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QAction,
    QDockWidget,
    QFileDialog,
    QGraphicsScene,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QUndoStack,
    QVBoxLayout,
    QWidget,
)

from core.backup_manager import BackupManager
from core.logger import app_logger
from models.tiles.hex_tile_item import HexTileItem
from models.tiles.square_tile_item import SquareTileItem
from models.tiles.tile_data import TileData
from ui.entity_tokens import EntityTokenLayer
from ui.fog_overlay import FogOfWarLayer
from ui.map_view import MapView

# Pause before an AI-controlled turn is played, so the turn highlight is visible.
AI_TURN_DELAY_MS = 600


class _EncounterSignals(QObject):
    """Bridges encounter listener calls (any thread) onto the Qt GUI thread."""

    turn_changed = pyqtSignal(object)


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
        # True while showing a host's map as a joined player (no local edits).
        self.read_only = False
        self._local_map_snapshot = None
        self.active_color = "#CCCCCC"

        # Multiplayer session
        self.session_manager = None

        # Heuristic AI adapter for enemy turns; built per encounter start.
        self._ai_adapter = None

        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.timeout.connect(self._auto_save)
        self._init_auto_save()

        self.init_ui()
        self.init_menu()

        # Redraw tokens when the entities panel adds/removes entities.
        from core.gameCreation.event_bus import EventBus
        EventBus.subscribe("entity_added", self._on_entities_changed)
        EventBus.subscribe("entity_removed", self._on_entities_changed)
        EventBus.subscribe("tile_modified", self._on_tile_modified)
        # Tile dialog saves and undo/redo go through the undo stack.
        self.undo_stack.indexChanged.connect(self._on_tile_modified)

        if rows is not None and cols is not None:
            self.init_grid(rows, cols)

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def init_ui(self):
        """Build the main layout: map (left) + side panel (right) in a QSplitter."""
        self.view = MapView()
        self.scene = QGraphicsScene(self)
        self.entity_tokens = EntityTokenLayer(self.scene)
        self.fog_overlay = FogOfWarLayer(self.scene, lambda: self.grid_type)
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
        self.session_panel.claim_requested.connect(self._on_claim_requested)
        self.session_panel.chat_submitted.connect(self._on_chat_submitted)
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

        # One gamemaster (and thus one encounter) per window; see get_gamemaster().
        self.gamemaster = None
        self._encounter_signals = _EncounterSignals()
        self._encounter_signals.turn_changed.connect(self._on_turn_changed)
        self.initiative_panel.next_turn_button.clicked.connect(self.next_turn)

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

        self._player_view_action = QAction("&Player View (Fog of War)", self)
        self._player_view_action.setShortcut("Ctrl+Shift+F")
        self._player_view_action.setCheckable(True)
        self._player_view_action.setChecked(False)
        self._player_view_action.toggled.connect(self.set_player_view)
        view_menu.addAction(self._player_view_action)

        self._reset_fog_action = QAction("Reset &Explored Area", self)
        self._reset_fog_action.setEnabled(False)
        self._reset_fog_action.triggered.connect(self.reset_explored_area)
        view_menu.addAction(self._reset_fog_action)

        # --- Encounter menu ---
        encounter_menu = menubar.addMenu("Encounter")
        self._start_encounter_action = QAction("&Start Encounter", self)
        self._start_encounter_action.setShortcut("Ctrl+Shift+E")
        self._start_encounter_action.triggered.connect(self.start_encounter)
        encounter_menu.addAction(self._start_encounter_action)

        self._next_turn_action = QAction("&Next Turn", self)
        self._next_turn_action.setShortcut("Ctrl+Shift+N")
        self._next_turn_action.triggered.connect(self.next_turn)
        encounter_menu.addAction(self._next_turn_action)

        self._end_encounter_action = QAction("&End Encounter", self)
        self._end_encounter_action.setShortcut("Ctrl+Shift+Q")
        self._end_encounter_action.triggered.connect(self.end_encounter)
        encounter_menu.addAction(self._end_encounter_action)

        encounter_menu.addSeparator()
        self._autoplay_action = QAction("&Auto-play Enemy Turns", self)
        self._autoplay_action.setCheckable(True)
        self._autoplay_action.setChecked(True)
        encounter_menu.addAction(self._autoplay_action)
        self._update_encounter_actions()

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
        self.fog_overlay.reset()
        self.refresh_entity_tokens()

    def refresh_entity_tokens(self):
        """Redraw entity tokens (and the fog overlay when in player view)."""
        try:
            self.entity_tokens.refresh()
            self.fog_overlay.refresh()
        except RuntimeError:  # window/scene already torn down
            pass

    def set_player_view(self, enabled):
        """Toggle the fog-of-war player view (DM view shows everything)."""
        self._reset_fog_action.setEnabled(bool(enabled))
        if self._player_view_action.isChecked() != bool(enabled):
            self._player_view_action.setChecked(bool(enabled))
            return  # toggled signal re-enters with the same value
        self.fog_overlay.set_enabled(bool(enabled))
        if enabled and not self.fog_overlay.has_viewers():
            self.statusBar().showMessage("Player view: no player entities on the map", 5000)

    def reset_explored_area(self):
        self.fog_overlay.reset()
        self.fog_overlay.refresh()

    def _on_tile_modified(self, _data=None):
        try:
            self.fog_overlay.refresh()
        except RuntimeError:
            pass

    def _on_entities_changed(self, _data=None):
        self.refresh_entity_tokens()

    def closeEvent(self, event):
        from core.gameCreation.event_bus import EventBus
        for name, cb in (
            ("entity_added", self._on_entities_changed),
            ("entity_removed", self._on_entities_changed),
            ("tile_modified", self._on_tile_modified),
        ):
            try:
                EventBus.unsubscribe(name, cb)
            except Exception:
                pass
        super().closeEvent(event)

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
        if self.read_only:
            self.statusBar().showMessage("Viewing the host's map (read-only)", 3000)
            return
        self.selected_tile = tile_item
        self.side_panel.load_tile(tile_item.tile_data, tile_item, self)

    # ------------------------------------------------------------------
    # Color mode
    # ------------------------------------------------------------------

    def activate_color_mode(self, color: str):
        """Enable color-painting mode with the given hex color."""
        if self.read_only:
            return
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
            "meta": {
                "author": "Fabio",
                "created": datetime.now().isoformat(),
                "grid_type": self.grid_type,
            },
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
            with open(filename, encoding="utf-8") as f:
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

        self._populate_scene(tiles)

        self.fog_overlay.reset()
        self.refresh_entity_tokens()
        app_logger.info(f"[Loaded] {len(tiles)} tiles loaded from {filename}")

    def _populate_scene(self, tile_dicts):
        """Add one tile item per serialized tile (``TileData.to_dict`` format) for ``self.grid_type``."""
        for td_data in tile_dicts:
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

        gm = self.get_gamemaster()
        self.session_manager = SessionManager(gamemaster=gm, settings=self.settings)
        self.session_manager.signals.chat_received.connect(self.session_panel.append_chat)
        self.session_manager.signals.disconnected.connect(self._on_session_ended)
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
        self.session_manager.signals.turn_changed.connect(self._on_remote_turn_changed)
        self.session_manager.signals.world_changed.connect(self.show_remote_world)
        self.session_manager.signals.entity_claimed.connect(self._on_remote_claim_changed)
        self.session_manager.signals.disconnected.connect(self._on_session_ended)
        self.session_manager.signals.connection_error.connect(
            lambda e: self.statusBar().showMessage(f"Connection error: {e}")
        )
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
        self._leave_remote_view()
        self._disconnect_action.setEnabled(False)
        self._session_dock.hide()
        self.session_panel.clear()
        self.statusBar().showMessage("Session ended")

    def _on_chat_submitted(self, message):
        if self.session_manager:
            self.session_manager.send_chat(message)

    # ------------------------------------------------------------------
    # Joined player: read-only view of the host's map
    # ------------------------------------------------------------------

    def show_remote_world(self, world_state):
        """Client side: replace the scene with the host's map (read-only, fog of war on).

        :param world_state: Dict in :func:`network.sync.serialize_world` format.
        """
        if not self.read_only:
            self._enter_remote_view()
        self.grid_type = world_state.get("tile_type", self.grid_type)
        self.scene.clear()
        self._populate_scene(world_state.get("tiles", {}).values())
        self._update_remote_vision()

        players = sorted(
            entity.get("name", "")
            for tile in world_state.get("tiles", {}).values()
            for entity in tile.get("entities", [])
            if str(entity.get("entity_type", "")).lower() == "player"
        )
        self.session_panel.set_claimable([] if self._my_claim() else players)

    def _my_claim(self):
        sm = self.session_manager
        return getattr(sm, "claimed_entity", None) if sm is not None else None

    def _update_remote_vision(self):
        claim = self._my_claim()
        # Before claiming a character, a joined player sees what the whole party sees.
        self.fog_overlay.viewer_names = {claim} if claim else None
        self.refresh_entity_tokens()

    def _on_claim_requested(self, entity_name):
        if self.session_manager is not None:
            self.session_manager.claim_entity(entity_name)

    def _on_remote_claim_changed(self, _entity_id, _player_id):
        if self.read_only:
            self._update_remote_vision()
            if self._my_claim():
                self.session_panel.set_claimable([])

    def _enter_remote_view(self):
        """Remember the local map and switch to read-only player view."""
        self._local_map_snapshot = {
            "grid_type": self.grid_type,
            "tiles": [i.tile_data.to_dict() for i in self.scene.items() if hasattr(i, "tile_data")],
            "map_path": self.current_map_path,
            "player_view": self._player_view_action.isChecked(),
        }
        self.read_only = True
        self.current_map_path = None  # auto-save must never write the host's map to a local file
        self.deactivate_color_mode()
        self.undo_stack.clear()
        self.gamemaster = None
        self.fog_overlay.reset()
        self.set_player_view(True)
        self._player_view_action.setEnabled(False)  # players can't lift the fog
        self._update_encounter_actions()
        self.statusBar().showMessage("Viewing the host's map (read-only)")

    def _leave_remote_view(self):
        """Restore the local map after a joined session ends."""
        if not self.read_only:
            return
        snapshot = self._local_map_snapshot or {}
        self.read_only = False
        self._local_map_snapshot = None
        self.fog_overlay.viewer_names = None
        self.fog_overlay.reset()
        self.grid_type = snapshot.get("grid_type", self.grid_type)
        self.current_map_path = snapshot.get("map_path")
        self.scene.clear()
        self._populate_scene(snapshot.get("tiles", []))
        self._player_view_action.setEnabled(True)
        self.set_player_view(snapshot.get("player_view", False))
        self.refresh_entity_tokens()
        self._update_encounter_actions()

    def _on_remote_turn_changed(self, entity_name, round_number):
        """Client side: show the host's current turn."""
        self._initiative_dock.show()
        self.initiative_panel.set_current_turn(entity_name, round_number)

    # ------------------------------------------------------------------
    # Encounter
    # ------------------------------------------------------------------

    def get_gamemaster(self):
        """Return the window's gamemaster, building it from the scene if needed.

        An existing gamemaster is kept while an encounter is active or a hosted
        session uses it; otherwise it is rebuilt so scene edits are picked up.
        """
        gm = self.gamemaster
        if gm is not None:
            hosting = bool(self.session_manager and self.session_manager.is_hosting)
            if gm.encounter.is_active or hosting:
                return gm
            gm.encounter.remove_listener(self._encounter_listener)
        gm = self._build_gamemaster_from_scene()
        gm.encounter.add_listener(self._encounter_listener)
        self.gamemaster = gm
        return gm

    def _encounter_listener(self, info):
        # May run on the host's asyncio thread: only emit a signal (queued to the GUI thread).
        self._encounter_signals.turn_changed.emit(info)

    def _update_encounter_actions(self):
        active = bool(self.gamemaster and self.gamemaster.encounter.is_active)
        self._start_encounter_action.setEnabled(not active and not self.read_only)
        self._next_turn_action.setEnabled(active)
        self._end_encounter_action.setEnabled(active)
        self.initiative_panel.next_turn_button.setEnabled(active)

    def start_encounter(self):
        from core.engine.encounter import EncounterError

        gm = self.get_gamemaster()
        # Built before start(): starting already announces the first turn.
        self._ai_adapter = self._build_ai_adapter(gm)
        # Shown before start(): the first turn's notification may replace it (e.g. AI status).
        self.statusBar().showMessage("Encounter started")
        try:
            order = gm.encounter.start()
        except EncounterError:
            self.statusBar().showMessage("Cannot start an encounter: no entities on the map")
            self._update_encounter_actions()
            return
        self.initiative_panel.set_initiative_order(order)
        self._initiative_dock.show()
        self._update_encounter_actions()

    def next_turn(self):
        from core.engine.encounter import EncounterError

        if not (self.gamemaster and self.gamemaster.encounter.is_active):
            return
        try:
            self.gamemaster.encounter.next_turn()
        except EncounterError:
            return

    def end_encounter(self):
        if self.gamemaster and self.gamemaster.encounter.is_active:
            self.gamemaster.encounter.end()
            self.statusBar().showMessage("Encounter ended")

    def _on_turn_changed(self, info):
        """GUI-thread slot for encounter notifications."""
        if info.entity_name is not None:
            # Re-read the order so HP changes (local or from network actions) are shown.
            if self.gamemaster is not None:
                self.initiative_panel.set_initiative_order(self.gamemaster.encounter.order())
            self.initiative_panel.set_current_turn(info.entity_name, info.round_number)
        else:
            self.initiative_panel.clear()
        self._update_encounter_actions()
        self.refresh_entity_tokens()
        self._maybe_schedule_ai_turn(info)

    # ------------------------------------------------------------------
    # AI-controlled enemy turns
    # ------------------------------------------------------------------

    @staticmethod
    def _build_ai_adapter(gm):
        from core.engine.ai.heuristic_adapter import HeuristicAIAdapter

        return HeuristicAIAdapter(
            entities_by_name={e.name: e for e in gm.game_entities},
            rng=random.Random(),
            world_tile_manager=gm.world_tile_manager,
        )

    def _claimed_entity_names(self):
        sm = self.session_manager
        if sm is None:
            return set()
        try:
            return set(sm.claimed_entities())
        except Exception:
            return set()

    def _is_ai_controlled(self, entity):
        if entity is None:
            return False
        kind = getattr(entity.entity_type, "value", entity.entity_type)
        if str(kind).strip().lower() != "enemy":
            return False
        return entity.name not in self._claimed_entity_names()

    def _maybe_schedule_ai_turn(self, info):
        """Schedule the AI to play the current turn when it is an unclaimed enemy's."""
        gm = self.gamemaster
        if info.entity_name is None or gm is None or not self._autoplay_action.isChecked():
            return
        enc = gm.encounter
        if not enc.is_active or enc.current_entity_name != info.entity_name:
            return
        if not self._is_ai_controlled(enc.current_entity):
            return
        if not any(
            str(getattr(e.entity_type, "value", e.entity_type)).strip().lower() == "player"
            and getattr(e, "hp", 1) > 0
            for e in gm.game_entities
        ):
            self.statusBar().showMessage("Encounter over: no players left")
            return
        name, round_number = info.entity_name, info.round_number
        QTimer.singleShot(AI_TURN_DELAY_MS, lambda: self._play_ai_turn(name, round_number))

    def _play_ai_turn(self, name, round_number):
        """Timer callback: play the AI turn unless the situation changed meanwhile."""
        gm = self.gamemaster
        if gm is None or not self._autoplay_action.isChecked():
            return
        enc = gm.encounter
        if not enc.is_active or enc.current_entity_name != name or enc.round_number != round_number:
            return
        if not self._is_ai_controlled(enc.current_entity):
            return
        if self._ai_adapter is None:
            self._ai_adapter = self._build_ai_adapter(gm)
        try:
            result = enc.take_ai_turn(self._ai_adapter)
        except Exception as e:  # never let an AI failure break the GUI
            app_logger.error(f"[AI Turn] {name}: {e}")
            self.statusBar().showMessage(f"{name}: AI turn failed ({e})")
            return
        if result.success:
            log = [line for line in (result.execution_log or []) if line]
            text = log[-1] if log else "acts"
            self.statusBar().showMessage(f"{name}: {text}")
        else:
            self.statusBar().showMessage(f"{name}: {result.error}")
        self.refresh_entity_tokens()

    def _build_gamemaster_from_scene(self):
        """Create a Gamemaster populated from the current scene."""
        from models.game_master import Gamemaster
        from models.world.world import World
        from models.world.world_tile_manager import WorldTileManager

        gm = Gamemaster()

        tile_datas = [item.tile_data for item in self.scene.items() if hasattr(item, "tile_data")]
        # Tile positions are (row, col); the tile manager's (x, y) bounds follow the same order.
        rows = max((td.position[0] for td in tile_datas), default=-1) + 1
        cols = max((td.position[1] for td in tile_datas), default=-1) + 1

        tile_manager = WorldTileManager(rows, cols, self.grid_type)
        # Use the scene's TileData objects so moves show up on the map.
        tile_manager.tiles = {td.position: td for td in tile_datas}
        for td in tile_datas:
            for entity in list(td.entities):
                entity.position = td.position
                tile_manager.entities.setdefault(td.position, []).append(entity)
                gm.add_entity(entity)

        gm.world = World(
            world_version="1.0",
            width=cols,
            height=rows,
            tile_type=self.grid_type,
            description="",
            map_data={},
            time_of_day="",
            weather_conditions="",
        )
        gm.world.tile_manager = tile_manager
        gm.world_tile_manager = tile_manager

        return gm

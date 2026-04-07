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

from enum import Enum

from models.tiles.tile_data import TileData
from models.tiles.square_tile_item import SquareTileItem
from models.tiles.hex_tile_item import HexTileItem
from core.backup_manager import BackupManager
from core.logger import app_logger
from ui.map_view import MapView


class AppViewState(Enum):
    """Current view state of the application."""
    MAP_EDITOR = "map_editor"
    ZONE_VIEW = "zone_view"
    COMBAT = "combat"


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
        self.back_to_menu_requested = None  # Callable set by MainController

        # Color mode state (replaces paint_mode_active / active_tile_preset)
        self.color_mode_active = False
        self.active_color = "#CCCCCC"

        # Multiplayer session
        self.session_manager = None
        # Measure mode
        self._measure_mode = None
        # View state tracking
        self._view_state = AppViewState.MAP_EDITOR

        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.timeout.connect(self._auto_save)
        self._init_auto_save()

        # Transition engine for animated state changes
        from ui.transitions.transition_engine import TransitionEngine
        from core.audio.ui_sound_manager import UISoundManager
        self._transition_engine = TransitionEngine(
            parent_widget=self, sound_manager=UISoundManager.instance())

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
        hint.setProperty("themeRole", "hint")
        map_layout.addWidget(hint)

        # Color mode indicator bar (shown when color mode is on)
        self.color_bar = QLabel(
            "  Color Mode — left-click to paint  |  right-click to sample  "
        )
        self.color_bar.setAlignment(Qt.AlignCenter)
        self.color_bar.setProperty("themeRole", "status-active")
        self.color_bar.hide()
        map_layout.addWidget(self.color_bar)

        # Compact toolbar: save buttons only
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(4, 2, 4, 2)
        back_btn = self.create_button("< Main Menu", self._back_to_menu)
        back_btn.setStyleSheet("font-weight: bold;")
        toolbar_layout.addWidget(back_btn)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.create_button("Save Scenario", self.save_scenario))
        toolbar_layout.addWidget(self.create_button("Save Map", self.save_map_dialog))
        map_layout.addWidget(toolbar)

        # --- Side panel (right column) ---
        from ui.panels.tile_side_panel import TileSidePanel
        self.side_panel = TileSidePanel(self)
        self.side_panel.setMinimumWidth(280)

        # --- Horizontal splitter ---
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(map_container)
        splitter.addWidget(self.side_panel)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
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

        # --- Asset library dock (hidden by default) ---
        from ui.panels.asset_manager_panel import AssetManagerPanel
        self._asset_panel = AssetManagerPanel(parent=self)
        self._asset_dock = QDockWidget("Asset Library", self)
        self._asset_dock.setWidget(self._asset_panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._asset_dock)
        self._asset_dock.hide()

        # --- Story timeline dock (hidden by default) ---
        from ui.panels.timeline_panel import TimelinePanel
        self._timeline_panel = TimelinePanel(parent=self)
        self._timeline_dock = QDockWidget("Story Timeline", self)
        self._timeline_dock.setWidget(self._timeline_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, self._timeline_dock)
        self._timeline_dock.hide()
        self._timeline_panel.navigate_to_tile.connect(self.pan_to_tile)
        self._story_timeline = None

        # --- Quick Search dock (hidden by default, Ctrl+K) ---
        from ui.panels.quick_search_panel import QuickSearchPanel
        self._search_panel = QuickSearchPanel(parent=self)
        self._search_panel.set_main_window(self)
        self._search_dock = QDockWidget("Quick Search", self)
        self._search_dock.setWidget(self._search_panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, self._search_dock)
        self._search_dock.hide()
        self._search_dock.visibilityChanged.connect(
            lambda vis: self._search_panel.refresh() if vis else None)

        # --- Template registry (lazy — loaded when builtins exist) ---
        from core.template_registry import TemplateRegistry
        self._template_registry = TemplateRegistry()
        try:
            self._template_registry.load_builtins()
        except Exception:
            pass  # templates dir may not exist yet

        self.statusBar().showMessage(
            "Right-click a tile to edit attributes  |  Ctrl+Z Undo  |  Ctrl+Y Redo"
        )

    def init_menu(self):
        """Build the menu bar."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        back_action = QAction("Back to Main Menu", self)
        back_action.setShortcut("Ctrl+M")
        back_action.triggered.connect(self._back_to_menu)
        file_menu.addAction(back_action)

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

        asset_toggle = self._asset_dock.toggleViewAction()
        asset_toggle.setText("&Asset Library")
        asset_toggle.setShortcut("Ctrl+L")
        view_menu.addAction(asset_toggle)

        timeline_toggle = self._timeline_dock.toggleViewAction()
        timeline_toggle.setText("Story &Timeline")
        timeline_toggle.setShortcut("Ctrl+T")
        view_menu.addAction(timeline_toggle)

        search_toggle = self._search_dock.toggleViewAction()
        search_toggle.setText("Quick &Search")
        search_toggle.setShortcut("Ctrl+K")
        view_menu.addAction(search_toggle)

        measure_action = QAction("&Measure Distance", self)
        measure_action.setShortcut("Ctrl+M")
        measure_action.setCheckable(True)
        measure_action.triggered.connect(self._toggle_measure_mode)
        view_menu.addAction(measure_action)
        self._measure_action = measure_action

        fog_action = QAction("&Fog of War", self)
        fog_action.setShortcut("Ctrl+F")
        fog_action.setCheckable(True)
        fog_action.triggered.connect(self._toggle_fog_of_war)
        view_menu.addAction(fog_action)
        self._fog_action = fog_action
        self._fog_overlay = None
        self._fog_state = None

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

        session_menu.addSeparator()
        return_action = QAction("Return to &Launcher", self)
        return_action.triggered.connect(self._return_to_launcher)
        session_menu.addAction(return_action)

        # --- Tools menu ---
        tools_menu = menubar.addMenu("Tools")
        simulate_action = QAction("&Simulate Combat...", self)
        simulate_action.triggered.connect(self._open_simulation)
        tools_menu.addAction(simulate_action)

        play_action = QAction("&Play Scenario...", self)
        play_action.setShortcut("Ctrl+P")
        play_action.triggered.connect(self._play_current_scenario)
        tools_menu.addAction(play_action)

        voice_settings_action = QAction("&Voice Settings...", self)
        voice_settings_action.triggered.connect(self._open_voice_settings)
        tools_menu.addAction(voice_settings_action)

        gen_tile_bg_action = QAction("&Generate Tile Backgrounds...", self)
        gen_tile_bg_action.triggered.connect(self._open_tile_bg_generator)
        tools_menu.addAction(gen_tile_bg_action)

        help_menu = menubar.addMenu("Help")
        tutorial_action = QAction("Tutorial", self)
        tutorial_action.triggered.connect(self._show_tutorial)
        help_menu.addAction(tutorial_action)

    def _show_tutorial(self):
        from ui.dialogs.tutorial_dialog import TutorialDialog
        TutorialDialog(self.settings, self).exec_()

    def _open_voice_settings(self):
        from ui.voice.voice_settings_dialog import VoiceSettingsDialog
        VoiceSettingsDialog(self.settings, self).exec_()

    def _open_tile_bg_generator(self):
        """Open the per-tile background generator dialog."""
        from ui.dialogs.tile_background_gen_dialog import TileBackgroundGenDialog
        TileBackgroundGenDialog(self, self).exec_()

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

    def _back_to_menu(self):
        """Return to the main menu / scenario overview."""
        if callable(self.back_to_menu_requested):
            self.back_to_menu_requested()

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

        # Save story timeline alongside map
        if self._story_timeline:
            timeline_path = map_path.parent / "story_timeline.json"
            try:
                self._story_timeline.save(timeline_path)
            except Exception as exc:
                app_logger.warning(f"[Timeline] Failed to save: {exc}")

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
            if hasattr(tile, "update_overlay_color"):
                tile.update_overlay_color()
            self.scene.addItem(tile)

        app_logger.info(f"[Loaded] {len(tiles)} tiles loaded from {filename}")
        self.scene.update()
        self.view.viewport().update()

        # Notify asset panel of workspace directory
        workspace_dir = Path(filename).parent
        self._asset_panel.set_workspace(workspace_dir)

        # Load story timeline if exists alongside map
        timeline_path = workspace_dir / "story_timeline.json"
        if timeline_path.exists():
            try:
                from models.story.story_timeline import StoryTimeline
                self._story_timeline = StoryTimeline.load(timeline_path)
                self._timeline_panel.set_timeline(self._story_timeline)
            except Exception as exc:
                app_logger.warning(f"[Timeline] Failed to load: {exc}")

        # Load user templates from workspace
        try:
            self._template_registry.load_user_templates(workspace_dir)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def pan_to_tile(self, tile_id: str) -> None:
        """Pan the map view to center on the tile with the given tile_id."""
        for item in self.scene.items():
            if hasattr(item, "tile_data") and item.tile_data.tile_id == tile_id:
                self.view.centerOn(item)
                break

    # ------------------------------------------------------------------
    # Story timeline integration
    # ------------------------------------------------------------------

    def _on_tile_add_to_timeline(self, tile_data) -> None:
        """Called from tile context menu: create a scene linked to this tile."""
        if self._story_timeline is None:
            from models.story.story_timeline import StoryTimeline
            self._story_timeline = StoryTimeline()
            self._timeline_panel.set_timeline(self._story_timeline)

        title = tile_data.user_label or f"Tile {tile_data.tile_id}"
        self._story_timeline.add_scene(title=title, tile_ids=[tile_data.tile_id])
        self._timeline_panel.set_timeline(self._story_timeline)
        self._timeline_dock.show()

    # ------------------------------------------------------------------
    # Simulation integration
    # ------------------------------------------------------------------

    def _open_simulation(self) -> None:
        """Open simulation dialog with entities from all tiles."""
        entity_dicts = []
        for item in self.scene.items():
            if hasattr(item, "tile_data"):
                for e in getattr(item.tile_data, "entities", []):
                    if hasattr(e, "to_dict"):
                        entity_dicts.append(e.to_dict())
        if not entity_dicts:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "Simulate Combat",
                                    "No entities on the map to simulate.")
            return
        from ui.dialogs.simulation_dialog import SimulationDialog
        dlg = SimulationDialog(entity_dicts, parent=self)
        dlg.exec_()

    def _open_simulation_for_tile(self, tile_data) -> None:
        """Open simulation for entities on a specific tile."""
        entity_dicts = [e.to_dict() for e in tile_data.entities if hasattr(e, "to_dict")]
        if not entity_dicts:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "Simulate Combat",
                                    "No entities on this tile to simulate.")
            return
        from ui.dialogs.simulation_dialog import SimulationDialog
        dlg = SimulationDialog(entity_dicts, parent=self)
        dlg.exec_()

    # ------------------------------------------------------------------
    # Play mode
    # ------------------------------------------------------------------

    def _play_current_scenario(self) -> None:
        """Launch the play session with the currently loaded map's tiles.

        Reloads directly from the map file on disk so the latest compiled
        data (backgrounds, zones, etc.) is always picked up.
        """
        tile_dicts = []

        # Prefer fresh load from disk to pick up latest compiled data
        map_path = getattr(self, "current_map_path", None)
        if map_path and Path(map_path).exists():
            try:
                with open(map_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                tile_dicts = raw.get("tiles", [])
            except Exception:
                tile_dicts = []

        # Fallback: serialize from the editor scene
        if not tile_dicts:
            for item in self.scene.items():
                if hasattr(item, "tile_data") and hasattr(item.tile_data, "to_dict"):
                    tile_dicts.append(item.tile_data.to_dict())

        if not tile_dicts:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "Play Scenario",
                                    "No tiles on the map. Load a scenario first.")
            return
        from ui.dialogs.play_session_dialog import PlaySessionDialog
        scenario_name = getattr(self, "_current_map_name", "Current Map")
        dlg = PlaySessionDialog(tile_dicts, scenario_name=scenario_name, parent=self)
        dlg.exec_()

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
        self.session_manager.signals.action_result_received.connect(self._on_action_result)
        self.session_manager.signals.turn_changed.connect(self._on_turn_changed)
        self.session_panel.chat_submitted.connect(self._on_chat_submitted)
        self.session_manager.host(port)

        self.session_panel.set_hosting(
            self.session_manager.join_address or f"localhost:{port}"
        )
        self._transition_engine.execute(
            "solo_to_hosting", incoming=self._session_dock)
        self._disconnect_action.setEnabled(True)
        self.statusBar().showMessage(f"Hosting session on port {port}")

        # Populate initiative panel with hosted entities
        entries = [
            {
                "name": e.name,
                "roll": 0,
                "hp": getattr(e, "hp", 0),
                "max_hp": getattr(e, "max_hp", 0),
                "entity_type": getattr(e, "entity_type", ""),
            }
            for e in gm.game_entities
        ]
        self.initiative_panel.set_initiative_order(entries)
        self._initiative_dock.show()

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
        self.session_manager.signals.action_result_received.connect(self._on_action_result)
        self.session_manager.signals.turn_changed.connect(self._on_turn_changed)
        self.session_manager.signals.entities_available.connect(
            self.session_panel.set_available_entities
        )
        self.session_panel.entity_claim_requested.connect(
            lambda eid: self.session_manager.claim_entity(eid)
        )
        self.session_panel.chat_submitted.connect(self._on_chat_submitted)
        self.session_manager.join(host_addr, port, player_name)

        self._transition_engine.execute(
            "join_to_connected", incoming=self._session_dock)
        self._disconnect_action.setEnabled(True)
        # Disable map editing for players (read-only view)
        self.side_panel.setEnabled(False)
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
        self._transition_engine.execute(
            "connected_to_disconnected", outgoing=self._session_dock)
        self.session_panel.clear()
        # Show dialog for unexpected disconnects (session_manager still set
        # means _disconnect_session() didn't clear it — connection was lost).
        unexpected = self.session_manager is not None
        if unexpected:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Connection Lost",
                "The multiplayer session has ended.\n"
                "You may have lost connection to the host.",
            )
            self.session_manager = None
        self.side_panel.setEnabled(True)
        self.statusBar().showMessage("Session ended")
        self._offer_return_to_launcher()

    def _offer_return_to_launcher(self):
        """Ask the user if they want to return to the main launcher."""
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Session Ended",
            "Return to the main menu?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self._return_to_launcher()

    def _return_to_launcher(self):
        """Close editor and reopen the launcher."""
        self.close()
        from entry_point import LaunchDialog
        from core.settings_manager import SettingsManager
        from core.theme_engine import ThemeEngine
        settings = self.settings if self.settings else SettingsManager()
        launcher = LaunchDialog(settings, ThemeEngine(settings))
        launcher.show()

    def _on_chat_submitted(self, message):
        if self.session_manager:
            self.session_manager.send_chat(message)

    def _request_action(self, action_type: str, params: dict):
        """Route an action through the network if in a session."""
        if self.session_manager and self.session_manager.is_connected:
            self.session_manager.request_action(action_type, params)

    def _on_action_result(self, success: bool, message: str):
        prefix = "Action" if success else "Action failed"
        self.statusBar().showMessage(f"{prefix}: {message}", 5000)
        if not success:
            self.session_panel.append_chat("System", f"Action rejected: {message}")

    def _toggle_fog_of_war(self, checked: bool):
        """Toggle fog of war overlay on the map."""
        if checked:
            tile_map = getattr(self, "_world_tile_manager", None)
            if tile_map is None:
                self.statusBar().showMessage("No tile map loaded for fog of war")
                self._fog_action.setChecked(False)
                return
            from core.engine.fog_state import FogOfWarState
            from core.engine.vision import compute_visible_tiles
            from ui.tools.fog_overlay import FogOverlay

            self._fog_state = FogOfWarState()
            self._fog_overlay = FogOverlay(self.scene, self.grid_size)

            # Compute initial visibility from all player entities
            world = getattr(self, "_world", None)
            if world:
                player_entities = []
                for e in getattr(world, "tile_manager", tile_map).entities.values():
                    for entity in e:
                        from models.entities.entity_type import EntityType
                        if getattr(entity, "entity_type", "") in (
                            EntityType.PLAYER, EntityType.ALLY, EntityType.COMPANION,
                        ):
                            pos = getattr(entity, "position", None)
                            vr = getattr(entity, "vision_range", None) or 12
                            if pos:
                                player_entities.append((pos, vr))
                if player_entities:
                    visible = compute_visible_tiles(world, player_entities)
                    self._fog_state.update(visible)
            self._fog_overlay.update(
                self._fog_state, tile_map.width, tile_map.height
            )
            self.statusBar().showMessage("Fog of war enabled")
        else:
            if self._fog_overlay:
                self._fog_overlay.clear()
                self._fog_overlay = None
            self._fog_state = None
            self.statusBar().showMessage("Fog of war disabled")

    def _toggle_measure_mode(self, checked: bool):
        """Toggle the two-click distance measurement mode."""
        if self._measure_mode is None:
            tile_map = getattr(self, "_world_tile_manager", None)
            if tile_map is None:
                self.statusBar().showMessage("No tile map loaded for measurement")
                self._measure_action.setChecked(False)
                return
            from ui.tools.measure_overlay import MeasureOverlay
            from ui.tools.measure_mode import MeasureMode

            overlay = MeasureOverlay(self.scene, self.grid_size)
            self._measure_mode = MeasureMode(
                self.scene, tile_map, overlay, self.statusBar()
            )
        self._measure_mode.toggle()
        self._measure_action.setChecked(self._measure_mode.active)

    def _on_turn_changed(self, entity_name: str, round_number: int):
        self.statusBar().showMessage(f"Round {round_number} - {entity_name}'s turn")
        self.initiative_panel.set_current_turn(entity_name, round_number)
        self._initiative_dock.show()

    # ------------------------------------------------------------------
    # Zone exploration wiring (Phase W1)
    # ------------------------------------------------------------------

    def _set_view_state(self, state: AppViewState) -> None:
        """Update the view state."""
        self._view_state = state

    def get_view_state(self) -> AppViewState:
        """Return the current view state."""
        return self._view_state

    def _on_tile_double_click(self, tile_data) -> None:
        """Enter a tile's zone view when double-clicked."""
        if not getattr(tile_data, "has_zones", False):
            return
        entrance = self._find_entrance_zone(tile_data)
        if entrance:
            self._enter_zone_view(tile_data, entrance.zone_id)

    def _find_entrance_zone(self, tile_data):
        for zone in tile_data.zones:
            if "entrance" in getattr(zone, "tags", []):
                return zone
        for zone in tile_data.zones:
            if "entrance" in zone.zone_id.lower() or "entrance" in zone.label.lower():
                return zone
        return tile_data.zones[0] if tile_data.zones else None

    def _enter_zone_view(self, tile_data, zone_id: str) -> None:
        from ui.exploration.zone_detail_widget import ZoneDetailWidget
        from models.exploration.zone_scene_data import build_zone_scene

        all_zones = {z.zone_id: z for z in tile_data.zones}
        zone = all_zones.get(zone_id)
        if not zone:
            return

        scene_data = build_zone_scene(zone, all_zones)

        if not hasattr(self, "_zone_widget") or self._zone_widget is None:
            self._zone_widget = ZoneDetailWidget(role="dm", parent=self)
            self._zone_widget.navigate_to_zone.connect(self._on_zone_navigate)
            self._zone_widget.navigate_to_map.connect(self._on_return_to_map)
            self._zone_widget.entity_clicked.connect(self._on_zone_entity_clicked)

        self._zone_widget.load_zone(scene_data)
        self._current_tile_data = tile_data
        self._current_zone_id = zone_id

        tile_label = getattr(tile_data, "user_label", "") or "Location"
        zone_label = zone.label
        self.statusBar().showMessage(f"Entered: {tile_label} — {zone_label}")
        self.update_window_title(f"{tile_label} — {zone_label}")
        self._set_view_state(AppViewState.ZONE_VIEW)

        from core.gameCreation.event_bus import EventBus
        from core.events import PLAYER_ENTERED_ZONE
        EventBus.emit(PLAYER_ENTERED_ZONE, {
            "zone_id": zone_id,
            "tile_id": getattr(tile_data, "tile_id", ""),
        })

    def _on_zone_navigate(self, target_zone_id: str) -> None:
        if not hasattr(self, "_current_tile_data") or not self._current_tile_data:
            return
        all_zones = {z.zone_id: z for z in self._current_tile_data.zones}
        target = all_zones.get(target_zone_id)
        if not target:
            return
        if target.locked:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "Locked", f"Locked (DC {target.lock_dc})")
            return

        from models.exploration.zone_scene_data import build_zone_scene
        scene_data = build_zone_scene(target, all_zones)
        self._zone_widget.load_zone(scene_data)
        self._current_zone_id = target_zone_id

    def _on_return_to_map(self) -> None:
        self._current_tile_data = None
        self._current_zone_id = None
        self.statusBar().showMessage("Returned to map")
        self.update_window_title()
        self._set_view_state(AppViewState.MAP_EDITOR)

    def _on_zone_entity_clicked(self, entity_name: str) -> None:
        if not hasattr(self, "_current_tile_data") or not self._current_tile_data:
            return
        all_zones = {z.zone_id: z for z in self._current_tile_data.zones}
        zone = all_zones.get(getattr(self, "_current_zone_id", None))
        if not zone:
            return

        entity = None
        for p in zone.placements:
            if hasattr(p.entity, "name") and p.entity.name == entity_name:
                entity = p.entity
                break

        if entity:
            from models.exploration.zone_interaction import get_inspect_text
            text = get_inspect_text(entity)
            self.statusBar().showMessage(text[:100])

    # ------------------------------------------------------------------
    # Sound + transition sync (Phases W2/W3)
    # ------------------------------------------------------------------

    def _sync_sound_theme(self, theme_name: str) -> None:
        """Sync the sound manager theme with the visual theme."""
        try:
            from core.audio.ui_sound_manager import UISoundManager
            UISoundManager.instance().set_theme(theme_name)
        except Exception:
            pass

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
            description="",
            map_data={},
            time_of_day="day",
            weather_conditions="clear",
        )
        gm.world.tile_manager = tile_manager

        return gm

    # ------------------------------------------------------------------
    # QoL: keyboard shortcuts + window title (Phase P6)
    # ------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:
        """Handle global keyboard shortcuts."""
        from PyQt5.QtCore import Qt
        key = event.key()

        # Escape: return to map from zone view
        if key == Qt.Key_Escape:
            if hasattr(self, "_current_zone_id") and self._current_zone_id:
                self._on_return_to_map()
                self.statusBar().showMessage("Returned to map")
                return

        super().keyPressEvent(event)

    def update_window_title(self, suffix: str = "") -> None:
        """Update the window title to reflect current state."""
        base = "DnD World Builder"
        if suffix:
            self.setWindowTitle(f"{base} — {suffix}")
        else:
            self.setWindowTitle(base)

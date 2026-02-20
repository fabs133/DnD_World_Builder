from PyQt5.QtWidgets import (
    QMainWindow, QGraphicsView, QGraphicsScene, QVBoxLayout, QPushButton, QWidget,
    QMenuBar, QAction, QFileDialog
)
from PyQt5.QtCore import Qt, QPointF
import json
import math
from models.tiles.tile_data import TileData
from models.tiles.square_tile_item import SquareTileItem
from models.tiles.hex_tile_item import HexTileItem
from PyQt5.QtWidgets import QUndoStack
from datetime import datetime
from core.backup_manager import BackupManager
from core.logger import app_logger
from pathlib import Path


def hex_tile_center(row, col, hex_size):
    """Calculate the pixel center of a flat-top hex tile at a given grid position.

    For flat-top hexagons with radius *hex_size*:
        - horizontal spacing = 1.5 * hex_size  (3/4 of the hex width)
        - vertical spacing   = sqrt(3) * hex_size  (full hex height)
        - odd columns are offset down by half the vertical spacing

    :param row: Row index in the grid.
    :param col: Column index in the grid.
    :param hex_size: Radius of each hexagon (center to vertex).
    :return: (x, y) pixel coordinates for the hex center.
    :rtype: tuple[float, float]
    """
    horiz = 1.5 * hex_size
    vert = math.sqrt(3) * hex_size
    x = col * horiz
    y = row * vert + (col % 2) * (vert / 2)
    return x, y


class MainWindow(QMainWindow):
    """
    Main application window for the DnD Map Editor.

    :param settings: Application settings object.
    :param grid_type: Type of grid to use ('square' or 'hex').
    :param rows: Number of rows for the grid.
    :param cols: Number of columns for the grid.
    """
    def __init__(self, settings, grid_type='square', rows=None, cols=None, *args, **kwargs):
        """
        Initialize the main window.

        :param settings: Application settings object.
        :param grid_type: Type of grid to use ('square' or 'hex').
        :param rows: Number of rows for the grid.
        :param cols: Number of columns for the grid.
        """
        super().__init__(*args, **kwargs)
        self.settings = settings
        self.setWindowTitle("DnD Map Editor")
        self.grid_type = grid_type
        self.paint_mode_active = False
        self.paint_mode_type = "visual"
        self.active_tile_preset = None
        self.selected_tile = None
        self.backup_manager = BackupManager()
        self.undo_stack = QUndoStack(self)
        
        self.init_ui()
        self.init_menu()

        # Only create a grid if starting fresh
        if rows is not None and cols is not None:
            self.init_grid(rows, cols)

    def init_ui(self):
        """
        Initialize the main UI components.
        """
        self.view = QGraphicsView()
        self.scene = QGraphicsScene(self)
        self.view.setScene(self.scene)

        layout = QVBoxLayout()
        layout.addWidget(self.view)

        self.trigger_btn = self.create_button("Open Trigger Graph", self.open_trigger_graph, enabled=False)
        layout.addWidget(self.trigger_btn)

        self.paint_toggle_button = self.create_button("🎨 Paint Mode", self.toggle_paint_mode, checkable=True)
        layout.addWidget(self.paint_toggle_button)

        self.mode_type_button = self.create_button("🧠 Logic Mode", self.toggle_paint_mode_type)
        layout.addWidget(self.mode_type_button)

        self.save_scenario_button = self.create_button("💾 Save Scenario", self.save_scenario)
        layout.addWidget(self.save_scenario_button)

        self.save_button = self.create_button("💾 Save Map", self.save_map_dialog)
        layout.addWidget(self.save_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def init_menu(self):
        """
        Initialize the menu bar and actions.
        """
        menubar = self.menuBar()
        edit_menu = menubar.addMenu("Edit")

        undo_action = self.undo_stack.createUndoAction(self, "&Undo")
        undo_action.setShortcut("Ctrl+Z")
        edit_menu.addAction(undo_action)

        redo_action = self.undo_stack.createRedoAction(self, "&Redo")
        redo_action.setShortcut("Ctrl+Y")
        edit_menu.addAction(redo_action)

    def init_grid(self, rows, cols):
        """
        Initialize the grid with the specified number of rows and columns.

        :param rows: Number of rows.
        :param cols: Number of columns.
        :raises ValueError: If grid_type is not supported.
        """
        if self.grid_type == 'square':
            self.create_square_grid(rows, cols, 50)
        elif self.grid_type == 'hex':
            self.create_hex_grid(rows, cols, 30)
        else:
            raise ValueError("Unsupported grid type. Use 'square' or 'hex'.")

    def create_square_grid(self, rows, cols, size):
        """
        Create a square grid of tiles.

        :param rows: Number of rows.
        :param cols: Number of columns.
        :param size: Size of each square tile.
        """
        for i in range(rows):
            for j in range(cols):
                tile_id = f"{i}_{j}"
                tile_data = TileData(tile_id=tile_id, position=(i, j))
                tile = SquareTileItem(j * size, i * size, size, tile_data, self)
                tile_data.tile_item = tile
                self.scene.addItem(tile)

    def create_hex_grid(self, rows, cols, hex_size):
        """
        Create a hexagonal grid of tiles.

        :param rows: Number of rows.
        :param cols: Number of columns.
        :param hex_size: Size of each hex tile.
        """
        for row in range(rows):
            for col in range(cols):
                x, y = hex_tile_center(row, col, hex_size)
                center = QPointF(x, y)
                tile_id = f"{row}_{col}"
                tile_data = TileData(tile_id=tile_id, position=(row, col))
                tile = HexTileItem(center, hex_size, tile_data, self)
                tile_data.tile_item = tile
                self.scene.addItem(tile)

    def toggle_paint_mode(self, checked):
        """
        Toggle the paint mode on or off.

        :param checked: Whether the paint mode is active.
        """
        self.paint_mode_active = checked
        mode_icon = "🧠" if self.paint_mode_type == "logic" else "🎨"
        self.paint_toggle_button.setText(f"{mode_icon} Paint Mode" if checked else "Paint Mode")

    def toggle_paint_mode_type(self):
        """
        Toggle between visual and logic paint modes.
        """
        self.paint_mode_type = "logic" if self.paint_mode_type == "visual" else "visual"
        self.mode_type_button.setText("🧠 Logic Mode" if self.paint_mode_type == "logic" else "🎨 Visual Mode")
        if self.paint_mode_active:
            mode_icon = "🧠" if self.paint_mode_type == "logic" else "🎨"
            self.paint_toggle_button.setText(f"{mode_icon} Paint Mode")

    def save_map_dialog(self):
        """
        Open a dialog to save the current map to a file.
        """
        path, _ = QFileDialog.getSaveFileName(self, "Save Map", "", "JSON Files (*.json)")
        if path:
            self.save_map_to_file(path)

    def save_map_to_file(self, filename="map.json"):
        """
        Save the current map to a JSON file.

        :param filename: Path to the file where the map will be saved.
        """
        map_path = Path(filename)
        should_backup = map_path.exists()  # Check before overwriting

        tile_data_list = [
            item.tile_data.to_dict()
            for item in self.scene.items()
            if isinstance(item, (SquareTileItem, HexTileItem))
        ]

        full_map_data = {
            "version": "1.0",
            "meta": {
                "author": "Fabio",
                "created": datetime.now().isoformat()
            },
            "tiles": tile_data_list
        }

        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(full_map_data, f, indent=2)

        app_logger.info(f"[Saved] Map written to {map_path}")

        # Only backup if this was overwriting a file
        if should_backup:
            self.backup_manager.backup_map(map_path)

    def select_tile(self, tile_item):
        """
        Select a tile in the scene.

        :param tile_item: The tile item to select.
        """
        if self.paint_mode_active:
            return
        self.selected_tile = tile_item
        self.trigger_btn.setEnabled(True)

    def open_trigger_graph(self):
        """
        Open the trigger editor dialog for the selected tile.
        """
        from dialogs.trigger_editor.editor_dialog import TriggerEditorDialog
        if self.selected_tile:
            dlg = TriggerEditorDialog(self.selected_tile.tile_data)
            dlg.exec_()

    def save_scenario(self):
        """
        Save the current scenario as a bundle (ZIP file).
        """
        from core.export_manager import ExportManager
        from PyQt5.QtWidgets import QFileDialog
        from pathlib import Path

        final_path_str, _ = QFileDialog.getSaveFileName(self, "Save Scenario As", "", "Scenario Bundle (*.zip)")
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

        # Move to final destination
        bundle_path.rename(final_path)
        temp_map_path.unlink()

        app_logger.info(f"[Exported] Scenario exported to {final_path}")

        # Backup if user overwrote an existing scenario
        if should_backup:
            self.backup_manager.backup_map(final_path)

    def initialize_default_map(self):
        """
        Initialize a new default map with standard grid size (25x25).
        """
        from models.tiles.tile_data import TileData

        self.scene.clear()
        self.grid_type = "square"  # Or use self.settings.get("grid_type", "square")

        rows, cols = 15, 15
        self.init_grid(rows, cols)

        for row in range(rows):
            for col in range(cols):
                tile_data = TileData(position=(row, col))

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

        app_logger.info(f"[Grid Initialized] Default map with {rows} rows x {cols} cols created.")


    def load_map_from_file(self, filename):
        """
        Load a map from a JSON file.

        :param filename: Path to the map file.
        """
        from models.tiles.tile_data import TileData

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
            app_logger.info(f"[Grid Initialized] Empty map loaded with {rows} rows x {cols} cols")
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

    def create_button(self, text, callback, checkable=False, enabled=True):
        """
        Utility function to create a QPushButton.

        :param text: Button label.
        :param callback: Function to call when the button is clicked.
        :param checkable: Whether the button is checkable.
        :param enabled: Whether the button is enabled.
        :return: The created QPushButton.
        """
        button = QPushButton(text)
        button.setCheckable(checkable)
        button.setEnabled(enabled)
        button.clicked.connect(callback)
        return button

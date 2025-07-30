from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QTextEdit, QFileDialog, QMessageBox, QLabel, QFormLayout, QLineEdit, QDialog, QInputDialog
)
from PyQt5.QtCore import Qt
from pathlib import Path
import json
import shutil
import zipfile
from core.export_manager import ExportManager
from datetime import datetime
from core.settings_manager import SettingsManager
from core.logger import AppLogger
from core.gameCreation.tiles_gui import MainMenuDialog


class ScenarioOverviewWidget(QWidget):
    def __init__(self, map_loader, settings_manager):
        super().__init__()
        self.map_loader = map_loader
        self.settings_manager = settings_manager
        self.export_manager = ExportManager()

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Scenario List
        self.scenario_list = QListWidget()
        self.scenario_list.itemSelectionChanged.connect(self.display_scenario_info)
        self.scenario_list.itemDoubleClicked.connect(self.open_selected_scenario)
        layout.addWidget(QLabel("Available Scenarios:"))
        layout.addWidget(self.scenario_list)

        # Buttons
        btn_layout = QHBoxLayout()
        self.new_btn = QPushButton("➕ New Scenario")
        self.load_btn = QPushButton("📂 Import Scenario")
        self.export_btn = QPushButton("📦 Export Scenario")
        self.new_btn.clicked.connect(self.create_new_scenario)
        self.load_btn.clicked.connect(self.import_scenario)
        self.export_btn.clicked.connect(self.export_scenario)

        btn_layout.addWidget(self.new_btn)
        btn_layout.addWidget(self.load_btn)
        btn_layout.addWidget(self.export_btn)

        layout.addLayout(btn_layout)

        # Scenario Info Panel
        self.info_panel = QTextEdit()
        self.info_panel.setReadOnly(True)
        layout.addWidget(QLabel("Scenario Info:"))
        layout.addWidget(self.info_panel)

        self.setLayout(layout)
        self.refresh_scenario_list()

    def refresh_scenario_list(self):
        self.scenario_list.clear()
        workspace = Path("workspace")
        workspace.mkdir(exist_ok=True)

        for folder in workspace.iterdir():
            if folder.is_dir() and (folder / "map.json").exists():
                self.scenario_list.addItem(folder.name)

    def display_scenario_info(self):
        selected = self.scenario_list.currentItem()
        if not selected:
            return

        scenario_name = selected.text()
        path = Path("workspace") / scenario_name / "map.json"

        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                meta = data.get("meta", {})
                tiles = data.get("tiles", [])
                triggers = sum(len(t.get("triggers", [])) for t in tiles)

                info = (
                    f"Name: {scenario_name}\n"
                    f"Author: {meta.get('author', 'Unknown')}\n"
                    f"Created: {meta.get('created', 'Unknown')}\n"
                    f"Tiles: {len(tiles)}\n"
                    f"Triggers: {triggers}\n"
                )
                self.info_panel.setText(info)

            except Exception as e:
                self.info_panel.setText(f"Failed to load scenario: {e}")

    def import_scenario(self):
        file, _ = QFileDialog.getOpenFileName(self, "Import Scenario (.zip)", "", "Zip Bundles (*.zip)")
        if not file:
            return

        zip_path = Path(file)
        import_dir = Path("workspace")
        import_dir.mkdir(exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            if "manifest.json" not in zf.namelist():
                QMessageBox.warning(self, "Invalid Bundle", "No manifest.json found in the bundle.")
                return

            manifest_data = json.loads(zf.read("manifest.json").decode("utf-8"))
            scenario_name = manifest_data.get("map_name", zip_path.stem).replace(" ", "_")
            target_dir = import_dir / scenario_name

            if target_dir.exists():
                res = QMessageBox.question(self, "Overwrite?",
                                        f"The scenario '{scenario_name}' already exists. Overwrite?",
                                        QMessageBox.Yes | QMessageBox.No)
                if res == QMessageBox.No:
                    return
                shutil.rmtree(target_dir)

            zf.extractall(target_dir)

        self.refresh_scenario_list()
        QMessageBox.information(self, "Import Successful", f"Scenario '{scenario_name}' imported.")

    def export_scenario(self):
        selected = self.scenario_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Select a scenario to export.")
            return

        name = selected.text()
        map_path = Path("workspace") / name / "map.json"
        bundle = self.export_manager.export_bundle(map_path)

        QMessageBox.information(self, "Export Complete", f"Exported to:\n{bundle}")

    def open_selected_scenario(self):
        selected = self.scenario_list.currentItem()
        if not selected:
            return

        scenario_name = selected.text()
        scenario_path = Path("workspace") / scenario_name / "map.json"
        self.map_loader(scenario_path)

    def create_new_scenario(self):
        # Step 1: Use the MainMenuDialog to configure grid settings
        dlg = MainMenuDialog(self.settings_manager, self)
        if dlg.exec_() != dlg.Accepted:
            return  # User cancelled

        # Step 2: Prompt for scenario name and author
        name, ok = QInputDialog.getText(self, "Scenario Name", "Enter scenario name:")
        if not ok or not name.strip():
            QMessageBox.warning(self, "Invalid Input", "Scenario name cannot be empty.")
            return

        name = name.strip().replace(" ", "_")
        scenario_path = Path("workspace") / name
        if scenario_path.exists():
            QMessageBox.warning(self, "Already Exists", "A scenario with this name already exists.")
            return

        author, ok = QInputDialog.getText(self, "Author", "Enter author name:")
        if not ok:
            return
        author = author.strip()

        # Step 3: Generate the map structure
        scenario_path.mkdir(parents=True, exist_ok=True)
        rows = self.settings_manager.get("default_rows", 25)
        cols = self.settings_manager.get("default_cols", 25)

        tiles = []
        for row in range(rows):
            for col in range(cols):
                tile = {
                    "tile_id": f"{row}_{col}",
                    "position": [row, col],
                    "terrain": "FLOOR",
                    "tags": [],
                    "user_label": None,
                    "note": None,
                    "overlay_color": None,
                    "last_updated": None,
                    "entities": [],
                    "triggers": []
                }
                tiles.append(tile)

        map_data = {
            "version": "1.0",
            "meta": {
                "map_name": name,
                "author": author,
                "created": datetime.now().isoformat(),
                "grid_type": self.settings_manager.get("grid_type", "square"),
                "rows": rows,
                "cols": cols
            },
            "tiles": tiles,
            "entities": []
        }

        with open(scenario_path / "map.json", "w", encoding="utf-8") as f:
            json.dump(map_data, f, indent=2)

        # Step 4: Update the UI
        self.refresh_scenario_list()
        matching_items = self.scenario_list.findItems(name, Qt.MatchExactly)
        if matching_items:
            self.scenario_list.setCurrentItem(matching_items[0])
            self.open_selected_scenario()
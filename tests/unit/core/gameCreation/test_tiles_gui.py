import json
import pytest
from PyQt5.QtWidgets import QInputDialog
from pathlib import Path as RealPath
from ui.scenario_overview import ScenarioOverviewWidget
from core.gameCreation.tiles_gui import MainMenuDialog
from PyQt5.QtWidgets import QInputDialog, QMessageBox


class DummySettings:
    def __init__(self):
        self._data = {
            "grid_type": "square",
            "default_rows": 3,
            "default_cols": 3
        }
        self.saved = False

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self.saved = True

    def save_settings(self):
        self.saved = True

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.set(key, value)


@pytest.fixture
def scenario_widget(qtbot, monkeypatch, tmp_path):
    # --- Redirect Path("workspace") ---
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    # Stub QMessageBox and QInputDialog
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: None)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: next(name_inputs))
    def patched_path(arg):
        if arg == "workspace":
            return workspace_root
        return RealPath(arg)

    monkeypatch.setattr("ui.scenario_overview.Path", patched_path)

    # --- Stub MainMenuDialog ---
    class DummyDialog(MainMenuDialog):
        def exec_(self):
            return self.Accepted  # Simulate acceptance

    monkeypatch.setattr("core.gameCreation.tiles_gui.MainMenuDialog", DummyDialog)

    # --- Stub user input for name and author ---
    name_inputs = iter([("TestScenario", True), ("TestAuthor", True)])
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: next(name_inputs))

    # --- Spy: was scenario opened? ---
    ScenarioOverviewWidget._opened = False

    def fake_open(self):
        ScenarioOverviewWidget._opened = True

    monkeypatch.setattr(ScenarioOverviewWidget, "open_selected_scenario", fake_open)

    # --- Create the widget ---
    settings = DummySettings()
    widget = ScenarioOverviewWidget(map_loader=lambda x: None, settings_manager=settings)
    qtbot.addWidget(widget)
    return widget


def test_create_new_scenario(tmp_path, scenario_widget):
    scenario_widget.create_new_scenario()

    map_file = tmp_path / "workspace" / "TestScenario" / "map.json"
    assert map_file.exists(), "Map file should have been created"

    with open(map_file) as f:
        data = json.load(f)
        assert data["meta"]["map_name"] == "TestScenario"
        assert data["meta"]["author"] == "TestAuthor"
        assert len(data["tiles"]) == 3 * 3  # default_rows * default_cols = 9 tiles

    assert ScenarioOverviewWidget._opened, "Scenario should have been opened"

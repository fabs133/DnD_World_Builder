import json
import pytest
from pathlib import Path as RealPath
from PyQt5.QtWidgets import QInputDialog, QMessageBox, QPushButton
from ui.scenario_overview import ScenarioOverviewWidget
from core.gameCreation.tiles_gui import MainMenuDialog


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

    def patched_path(arg):
        if arg == "workspace":
            return workspace_root
        return RealPath(arg)

    monkeypatch.setattr("ui.scenario_overview.Path", patched_path)

    # --- Stub QMessageBox to avoid GUI dialogs ---
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: None)

    # --- Stub QInputDialog.getText for name and author ---
    name_inputs = iter([("TestScenario", True), ("TestAuthor", True)])
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: next(name_inputs))

    # --- Stub MainMenuDialog to simulate button click ---
    class DummyDialog(MainMenuDialog):
        def __init__(self, settings, parent=None):
            super().__init__(settings, parent)

        def exec_(self):
            # Programmatically click the "Create New Map" button
            for btn in self.findChildren(QPushButton):
                if btn.text() == "Create New Map":
                    btn.click()
                    break
            return self.Accepted

    monkeypatch.setattr("core.gameCreation.tiles_gui.MainMenuDialog", DummyDialog)

    # --- Spy on scenario opening ---
    ScenarioOverviewWidget._opened = False
    monkeypatch.setattr(
        ScenarioOverviewWidget,
        "open_selected_scenario",
        lambda self: setattr(ScenarioOverviewWidget, "_opened", True)
    )

    # --- Create widget ---
    settings = DummySettings()
    widget = ScenarioOverviewWidget(map_loader=lambda x: None, settings_manager=settings)
    qtbot.addWidget(widget)
    return widget

import json
import shutil
import zipfile
from pathlib import Path

import pytest
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QListWidgetItem

import ui.scenario_overview as so_mod
from ui.scenario_overview import ScenarioOverviewWidget

@pytest.fixture(autouse=True)
def workspace(tmp_path, monkeypatch):
    # Point the widget to use tmp_path / "workspace"
    ws = tmp_path / "workspace"
    monkeypatch.chdir(tmp_path)
    return ws

@pytest.fixture
def widget(qapp, workspace):
    # map_loader and settings_manager can be simple lambdas/placeholders
    ml = lambda path: setattr(widget_obj, "loaded_path", path)
    sm = object()
    global widget_obj
    widget_obj = ScenarioOverviewWidget(map_loader=ml, settings_manager=sm)
    return widget_obj

def create_scenario_dir(workspace, name, tiles=None, meta=None):
    # Create workspace/name/map.json
    d = workspace / name
    d.mkdir(parents=True, exist_ok=True)
    data = {
        "meta": meta or {"author": "A", "created": "T"},
        "tiles": tiles or [{"triggers": [1, 2]}, {"triggers": []}]
    }
    with open(d / "map.json", "w", encoding="utf-8") as f:
        json.dump(data, f)
    return d

def test_refresh_and_display_info(widget, workspace):
    # No scenarios initially
    assert widget.scenario_list.count() == 0

    # Create two scenarios
    create_scenario_dir(workspace, "One", tiles=[{"triggers":[1]}])
    create_scenario_dir(workspace, "Two", tiles=[{}, {}, {}], meta={"author":"Bob","created":"Now"})

    widget.refresh_scenario_list()
    # Should have two items (order arbitrary)
    names = {widget.scenario_list.item(i).text() for i in range(widget.scenario_list.count())}
    assert names == {"One", "Two"}

    # Display info for "Two"
    # find the item
    for i in range(widget.scenario_list.count()):
        if widget.scenario_list.item(i).text() == "Two":
            widget.scenario_list.setCurrentRow(i)
            break
    widget.display_scenario_info()
    info = widget.info_panel.toPlainText().splitlines()
    assert "Name: Two" in info[0]
    assert "Author: Bob" in info[1]
    assert "Tiles: 3" in info[3]
    # triggers count = sum triggers lists length
    assert "Triggers: 0" in info[4] or "Triggers: 1" in info[4]

def test_import_scenario(monkeypatch, widget, workspace, tmp_path, capsys):
    # Build a zip file with manifest.json and map.json
    scenario_name = "ZipScn"
    manifest = {"map_name": "My Map"}
    # temp source zip
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.writestr("map.json", json.dumps({"meta":{}, "tiles": []}))
    # stub QFileDialog to return our zip path
    monkeypatch.setattr(QFileDialog, "getOpenFileName",
                        lambda *args, **kwargs: (str(zip_path), None))
    # stub QMessageBox.question so overwrite behavior is Yes
    monkeypatch.setattr(QMessageBox, "question",
                        lambda *args, **kwargs: QMessageBox.Yes)
    # capture information and warnings
    infos = []
    monkeypatch.setattr(QMessageBox, "information",
                        lambda *args, **kwargs: infos.append(("info", args[1])))
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *args, **kwargs: infos.append(("warn", args[1])))

    widget.import_scenario()
    # After import, workspace/My_Map must exist
    target = workspace / "My_Map"
    assert target.exists() and (target / "map.json").exists()
    widget.refresh_scenario_list()
    assert any(widget.scenario_list.item(i).text() == "My_Map" for i in range(widget.scenario_list.count()))
    # QMessageBox.information(title, text) → we captured title in args[1]
    # In code you use: QMessageBox.information(self, "Import Successful", ...)
    assert ("info", "Import Successful") in infos

def test_import_invalid_bundle(monkeypatch, widget):
    # Create a zip without manifest
    zip_path = Path("no_manifest.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("not_manifest.txt", "oops")
    monkeypatch.setattr(QFileDialog, "getOpenFileName",
                        lambda *args, **kwargs: (str(zip_path), None))
    calls = []
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *args, **kwargs: calls.append(args[1]))
    widget.import_scenario()
    assert "Invalid Bundle" in calls[0]

def test_export_scenario(monkeypatch, widget, workspace):
    # Prepare a scenario dir and populate the list
    create_scenario_dir(workspace, "ExpScn")
    widget.refresh_scenario_list()
    # select it
    widget.scenario_list.setCurrentRow(0)
    # stub export_manager.export_bundle
    bundle_path = workspace / "out.zip"
    monkeypatch.setattr(widget.export_manager, "export_bundle",
                        lambda mp: bundle_path)
    infos = []
    monkeypatch.setattr(QMessageBox, "information",
                        lambda *args, **kwargs: infos.append(args[1]))

    widget.export_scenario()
    # We capture the title argument (args[1]), which in code is "Export Complete"
    assert infos and infos[0] == "Export Complete"

def test_open_selected_scenario(widget, workspace):
    # Prepare scenario dir
    d = create_scenario_dir(workspace, "TestScn")
    widget.refresh_scenario_list()
    # select it
    widget.scenario_list.setCurrentRow(0)
    # call open_selected_scenario
    widget.open_selected_scenario()
    # map_loader is called with the (relative) Path("workspace/.../map.json")
    rel = Path("workspace") / "TestScn" / "map.json"
    assert getattr(widget_obj, "loaded_path") == rel

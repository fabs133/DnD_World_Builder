import pytest
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton
from pathlib import Path

# Before import, monkeypatch the UI classes
import importlib

def setup_ui_mocks(monkeypatch):
    # Dummy ScenarioOverviewWidget
    class DummyScenarioOverview(QWidget):
        def __init__(self, map_loader, settings_manager):
            super().__init__()
            self.map_loader = map_loader
            self.settings_manager = settings_manager
            self.new_btn = QPushButton('New')

    # Dummy MainWindow
    class DummyMainWindow(QWidget):
        def __init__(self, settings_manager):
            super().__init__()
            self.settings_manager = settings_manager
            self.loaded_path = None
            self.default_initialized = False

        def load_map_from_file(self, path):
            self.loaded_path = path

        def initialize_default_map(self):
            self.default_initialized = True  # Track call if needed


    monkeypatch.setattr('ui.scenario_overview.ScenarioOverviewWidget', DummyScenarioOverview)
    monkeypatch.setattr('ui.main_window.MainWindow', DummyMainWindow)

@pytest.fixture(autouse=True)
def ensure_app(qtbot):
    # Ensure a QApplication exists
    return QApplication.instance() or QApplication([])

@pytest.fixture
def controller(monkeypatch, qtbot):
    setup_ui_mocks(monkeypatch)
    # Now import MainController
    from core.gameCreation.main_controller import MainController
    ctrl = MainController()
    qtbot.addWidget(ctrl)
    return ctrl


def test_initial_state(controller):
    # Only scenario overview in stack
    stack = controller.stack
    assert stack.count() == 1
    assert stack.widget(0) is controller.scenario_overview
    assert controller.map_editor is None


def test_start_new_map(controller):
    # Simulate clicking the new button
    callback = controller.scenario_overview.new_btn.clicked
    # Connect should have assigned controller.start_new_map
    # Instead of introspecting signal, directly call start_new_map
    controller.start_new_map()

    # Now map_editor should be set
    assert controller.map_editor is not None
    # Stack should now have 2 widgets
    assert controller.stack.count() == 2
    assert controller.stack.currentWidget() is controller.map_editor
    # The map_editor.settings_manager is same as controller.settings
    assert controller.map_editor.settings_manager is controller.settings


def test_load_existing_map(controller):
    # Create fake file path
    p = Path('fake_map.json')
    # Call load_existing_map
    controller.load_existing_map(p)

    assert controller.map_editor is not None
    # Should have loaded the file
    assert controller.map_editor.loaded_path == str(p)
    # Stack current widget is map_editor
    assert controller.stack.currentWidget() is controller.map_editor


def test_replace_existing_editor(controller):
    # First start new map
    controller.start_new_map()
    first_editor = controller.map_editor
    # Then load existing map
    controller.load_existing_map(Path('other.json'))
    # Should have replaced editor instance
    assert controller.map_editor is not first_editor
    assert controller.stack.count() == 2
    assert controller.stack.currentWidget() is controller.map_editor

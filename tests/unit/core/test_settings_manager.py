import json
import os
import pytest

from core.settings_manager import SettingsManager, DEFAULT_SETTINGS, CONFIG_VERSION

def test_default_config_created(tmp_path, capsys):
    # point at a non-existent file inside a nested dir
    config_file = tmp_path / "config" / "settings.json"
    assert not config_file.exists()

    mgr = SettingsManager(path=str(config_file))

    # directory and file must now exist
    assert config_file.exists()
    # settings should be exactly DEFAULT_SETTINGS (no config_version)
    assert mgr.settings == DEFAULT_SETTINGS
    assert "config_version" not in mgr.settings

    # user should see a “No config found…” print
    captured = capsys.readouterr()
    assert f"No config found at {config_file}" in captured.out

def test_get_and_set(tmp_path):
    config_file = tmp_path / "settings.json"
    mgr = SettingsManager(path=str(config_file))

    # default get
    assert mgr.get("grid_type") == DEFAULT_SETTINGS["grid_type"]

    # set something new
    mgr.set("grid_type", "hex")
    assert mgr.get("grid_type") == "hex"

    # and verify it was written to disk
    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert data["grid_type"] == "hex"

def test_item_accessors(tmp_path):
    config_file = tmp_path / "settings.json"
    mgr = SettingsManager(path=str(config_file))

    mgr["theme"] = "dark"
    assert mgr["theme"] == "dark"

    # persists in the file as well
    on_disk = json.loads(config_file.read_text(encoding="utf-8"))
    assert on_disk["theme"] == "dark"

def test_migration_from_version_0(tmp_path, capsys):
    # create a v0 config (missing grid_size)
    cfg_dir = tmp_path / "conf"
    cfg_dir.mkdir()
    config_file = cfg_dir / "settings.json"
    initial = {
        "config_version": 0,
        "some_key": "value"
        # grid_size not present here
    }
    config_file.write_text(json.dumps(initial), encoding="utf-8")

    mgr = SettingsManager(path=str(config_file))

    # user sees migration message
    captured = capsys.readouterr()
    assert "Migrating config from version 0 to 1" in captured.out

    # original keys still there
    assert mgr.settings["some_key"] == "value"
    # grid_size was added, and config_version bumped
    assert mgr.settings["grid_size"] == DEFAULT_SETTINGS["grid_size"]
    assert mgr.settings["config_version"] == CONFIG_VERSION

    # and file was updated accordingly
    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert data["grid_size"] == DEFAULT_SETTINGS["grid_size"]
    assert data["config_version"] == CONFIG_VERSION

def test_invalid_json_resets_to_default(tmp_path, capsys):
    config_file = tmp_path / "settings.json"
    # write a broken JSON
    config_file.write_text("{ this is not valid json ")

    mgr = SettingsManager(path=str(config_file))

    # should print an error + reset
    captured = capsys.readouterr()
    assert "Error loading config" in captured.out
    assert "Resetting to default config" in captured.out

    # settings = DEFAULT_SETTINGS, and file was overwritten
    assert mgr.settings == DEFAULT_SETTINGS
    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert data == DEFAULT_SETTINGS

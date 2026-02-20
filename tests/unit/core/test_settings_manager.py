import json
import logging
import os
import pytest

from core.settings_manager import SettingsManager, DEFAULT_SETTINGS, CONFIG_VERSION

def test_default_config_created(tmp_path, caplog):
    config_file = tmp_path / "config" / "settings.json"
    assert not config_file.exists()

    with caplog.at_level(logging.DEBUG):
        mgr = SettingsManager(path=str(config_file))

    assert config_file.exists()
    assert mgr.settings == DEFAULT_SETTINGS
    assert "config_version" not in mgr.settings
    assert f"No config found at {config_file}" in caplog.text

def test_get_and_set(tmp_path):
    config_file = tmp_path / "settings.json"
    mgr = SettingsManager(path=str(config_file))

    assert mgr.get("grid_type") == DEFAULT_SETTINGS["grid_type"]

    mgr.set("grid_type", "hex")
    assert mgr.get("grid_type") == "hex"

    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert data["grid_type"] == "hex"

def test_item_accessors(tmp_path):
    config_file = tmp_path / "settings.json"
    mgr = SettingsManager(path=str(config_file))

    mgr["theme"] = "dark"
    assert mgr["theme"] == "dark"

    on_disk = json.loads(config_file.read_text(encoding="utf-8"))
    assert on_disk["theme"] == "dark"

def test_migration_from_version_0(tmp_path, caplog):
    cfg_dir = tmp_path / "conf"
    cfg_dir.mkdir()
    config_file = cfg_dir / "settings.json"
    initial = {
        "config_version": 0,
        "some_key": "value"
    }
    config_file.write_text(json.dumps(initial), encoding="utf-8")

    with caplog.at_level(logging.DEBUG):
        mgr = SettingsManager(path=str(config_file))

    assert "Migrating config from version 0 to 1" in caplog.text
    assert mgr.settings["some_key"] == "value"
    assert mgr.settings["grid_size"] == DEFAULT_SETTINGS["grid_size"]
    assert mgr.settings["config_version"] == CONFIG_VERSION

    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert data["grid_size"] == DEFAULT_SETTINGS["grid_size"]
    assert data["config_version"] == CONFIG_VERSION

def test_invalid_json_resets_to_default(tmp_path, caplog):
    config_file = tmp_path / "settings.json"
    config_file.write_text("{ this is not valid json ")

    with caplog.at_level(logging.DEBUG):
        mgr = SettingsManager(path=str(config_file))

    assert "Error loading config" in caplog.text
    assert "Resetting to default config" in caplog.text

    assert mgr.settings == DEFAULT_SETTINGS
    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert data == DEFAULT_SETTINGS

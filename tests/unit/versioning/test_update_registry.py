import pytest
from versioning.update_registry import update_registry
import versioning.migrations.user_profile as up_mod
import versioning.migrations.settings as settings_mod
import versioning.migrations.map_data as map_mod

def test_top_level_keys():
    assert set(update_registry.keys()) == {"UserProfile", "Settings", "Map"}

def test_userprofile_versions():
    user_map = update_registry["UserProfile"]
    # should have mappings for versions 0 and 1
    assert set(user_map.keys()) == {0, 1}
    # check they point to the correct functions
    assert user_map[0] == up_mod.migrate_v0_to_v1
    assert user_map[1] == up_mod.migrate_v1_to_v2

def test_settings_versions():
    settings_map = update_registry["Settings"]
    assert set(settings_map.keys()) == {0}
    # version 0 migration is explicitly None
    assert settings_map[0] is None

def test_map_versions():
    map_map = update_registry["Map"]
    assert set(map_map.keys()) == {0}
    assert map_map[0] is None

def test_all_non_none_are_callable():
    for category, versions in update_registry.items():
        for ver, fn in versions.items():
            if fn is not None:
                assert callable(fn), f"{category}[{ver}] is not callable"

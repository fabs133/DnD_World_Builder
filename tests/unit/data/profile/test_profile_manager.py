import json
import pytest
from pathlib import Path

import data.profile.profile_manager as pm
from data.profile.profile_manager import UserProfile

def test_default_userprofile_data():
    up = UserProfile(name="Alice", profile_version=1)
    # Basic fields set correctly
    assert up.name == "Alice"
    assert up.profile_version == 1
    # Default payload
    assert up.data == {
        "characters": [],
        "current_character": None,
        "preferences": {}
    }
    # Accessors on the fresh profile
    assert up.get_characters() == []
    assert up.get_current_character() is None

def test_preferences_set_and_get():
    up = UserProfile("Bob", 1)
    # Absent key yields None or provided default
    assert up.get_preference("foo") is None
    assert up.get_preference("foo", default="bar") == "bar"

    # Setting and then getting
    up.set_preference("color", "red")
    assert up.get_preference("color") == "red"

def test_save_writes_json_file(tmp_path):
    data = {
        "characters": ["Zero"],
        "current_character": "Zero",
        "preferences": {"a": 1}
    }
    up = UserProfile("Carol", 2, data=data)
    dst = tmp_path / "profile.json"
    up.save(dst)

    # File must exist and contain exactly `data`
    assert dst.exists()
    on_disk = json.loads(dst.read_text(encoding="utf-8"))
    assert on_disk == data

def test_load_user_profile_triggers_update(monkeypatch, tmp_path):
    # 1) Prepare a profile file with version=1
    initial = {
        "version": 1,
        "characters": ["X"],
        "current_character": "X",
        "preferences": {}
    }
    pfile = tmp_path / "user.json"
    pfile.write_text(json.dumps(initial), encoding="utf-8")

    # 2) Tell UserProfile what current VERSION is
    monkeypatch.setattr(UserProfile, "VERSION", 2)

    # 3) Stub out the backup & updater & logger
    called = {"backup": False, "updates": []}

    def fake_backup(path):
        assert str(path) == str(pfile)
        called["backup"] = True

    monkeypatch.setattr(pm, "create_backup", fake_backup)

    def fake_update(profile_id, data, ver):
        # verify arguments
        assert profile_id == "UserProfile"
        assert ver == 1
        new_data = {
            "version": 2,
            "characters": data["characters"],
            "current_character": data["current_character"],
            "preferences": data["preferences"],
            "migrated": True
        }
        new_version = 2
        called["updates"].append((data, ver))
        return new_data, new_version

    monkeypatch.setattr(pm.updater, "update", fake_update)

    # suppress actual logging, but record
    logs = []
    monkeypatch.setattr(pm.logger, "info", lambda msg: logs.append(msg))

    # 4) Monkey-patch from_dict so we can observe the return
    monkeypatch.setattr(UserProfile, "from_dict",
                        staticmethod(lambda d: ("FROM_DICT", d)))

    # 5) Call the loader
    result = UserProfile.load_user_profile(str(pfile))

    # --- Assertions ---
    # backup was created
    assert called["backup"] is True

    # updater.update was invoked once
    assert len(called["updates"]) == 1

    # logger.info contains both out-of-date and updated messages
    assert any("Profile out of date" in m for m in logs)
    assert any("Profile updated to v2" in m for m in logs)

    # the file on disk was overwritten with new_data
    on_disk = json.loads(pfile.read_text(encoding="utf-8"))
    assert on_disk.get("migrated", False) is True
    assert on_disk["version"] == 2

    # the loader returns whatever our from_dict stub returned
    assert result == ("FROM_DICT", on_disk)

def test_load_user_profile_no_update_if_current(monkeypatch, tmp_path):
    # Prepare a profile file with version matching VERSION
    initial = {"version": 5, "foo": "bar"}
    pfile = tmp_path / "profile2.json"
    pfile.write_text(json.dumps(initial), encoding="utf-8")

    # Set VERSION to 5 so no migration
    monkeypatch.setattr(UserProfile, "VERSION", 5)

    # Track calls
    calls = {"backup": 0, "update": 0}
    monkeypatch.setattr(pm, "create_backup",
                        lambda path: calls.__setitem__("backup", calls["backup"]+1))
    monkeypatch.setattr(pm.updater, "update",
                        lambda *args, **kwargs: calls.__setitem__("update", calls["update"]+1))

    # Stub from_dict for final return
    monkeypatch.setattr(UserProfile, "from_dict",
                        staticmethod(lambda d: ("UNCHANGED", d)))

    result = UserProfile.load_user_profile(str(pfile))

    # No backup or update calls
    assert calls["backup"] == 0
    assert calls["update"] == 0

    # Returns from_dict(initial)
    assert result == ("UNCHANGED", initial)

def test_load_static_method_creates_profile(tmp_path):
    # Write an arbitrary JSON payload
    payload = {"abc": 123}
    pfile = tmp_path / "foo.json"
    pfile.write_text(json.dumps(payload), encoding="utf-8")

    prof = UserProfile.load(str(pfile), "MyName")
    # It should be a UserProfile
    assert isinstance(prof, UserProfile)
    # Name comes from the second argument
    assert prof.name == "MyName"
    # profile_version is the raw JSON dict
    assert prof.profile_version == payload
    # data falls back to defaults
    assert prof.data == {
        "characters": [],
        "current_character": None,
        "preferences": {}
    }

def test_load_user_profile_raises_on_bad_json(tmp_path):
    # Invalid JSON should bubble up JSONDecodeError
    pfile = tmp_path / "bad.json"
    pfile.write_text("{ not valid json")

    with pytest.raises(json.JSONDecodeError):
        UserProfile.load_user_profile(str(pfile))

import pytest
import shutil
from pathlib import Path
import datetime as real_datetime

import core.backup_manager as bm_mod
from core.backup_manager import BackupManager

@pytest.fixture
def backup_dir(tmp_path):
    return tmp_path / "backups"

@pytest.fixture(autouse=True)
def isolate_datetime(monkeypatch):
    """
    Make sure bm_mod.datetime.now() is under our control.
    By default do nothing; individual tests can override.
    """
    # leave datetime.now as-is unless overridden below
    yield

def test_ctor_creates_directory(backup_dir):
    mgr = BackupManager(backup_dir=str(backup_dir), max_backups_per_map=3)
    assert backup_dir.exists() and backup_dir.is_dir()

def test_backup_nonexistent_map(tmp_path, backup_dir):
    mgr = BackupManager(backup_dir=str(backup_dir), max_backups_per_map=3)
    missing = tmp_path / "no_such_map.json"
    # should silently return without error
    mgr.backup_map(missing)
    assert list(backup_dir.iterdir()) == []

def test_backup_map_creates_file(tmp_path, backup_dir, monkeypatch):
    # freeze datetime.now()
    fixed = real_datetime.datetime(2021,1,1,12,34,56)
    monkeypatch.setattr(bm_mod.datetime, 'now', lambda: fixed)

    mgr = BackupManager(backup_dir=str(backup_dir), max_backups_per_map=3)
    # create a dummy map
    src = tmp_path / "mymap.json"
    src.write_text("hello")

    mgr.backup_map(src)

    # exactly one backup exists
    files = list(backup_dir.glob("mymap_*.json"))
    assert len(files) == 1

    # name contains our timestamp
    expected = f"mymap_{fixed.strftime('%Y%m%d_%H%M%S')}.json"
    assert files[0].name == expected

    # content was copied
    assert files[0].read_text() == "hello"

def test_prune_old_backups(tmp_path, backup_dir, monkeypatch):
    # set up four distinct timestamps
    times = [
        real_datetime.datetime(2021,1,1,0,0,1),
        real_datetime.datetime(2021,1,1,0,0,2),
        real_datetime.datetime(2021,1,1,0,0,3),
        real_datetime.datetime(2021,1,1,0,0,4),
    ]
    def pop_time():
        return times.pop(0)
    # stub datetime.now to pop off our list
    monkeypatch.setattr(bm_mod.datetime, 'now', pop_time)

    mgr = BackupManager(backup_dir=str(backup_dir), max_backups_per_map=2)
    src = tmp_path / "mymap.json"
    src.write_text("x")

    # create 4 backups; after each, old ones beyond the two most recent get pruned
    for _ in range(4):
        mgr.backup_map(src)

    all_backups = sorted(backup_dir.glob("mymap_*.json"))
    # only 2 newest should remain
    assert len(all_backups) == 2

    kept_names = {p.name for p in all_backups}
    expected_names = {
        f"mymap_{real_datetime.datetime(2021,1,1,0,0,4).strftime('%Y%m%d_%H%M%S')}.json",
        f"mymap_{real_datetime.datetime(2021,1,1,0,0,3).strftime('%Y%m%d_%H%M%S')}.json",
    }
    assert kept_names == expected_names

import pytest
from pathlib import Path
from unittest.mock import patch
import datetime as real_datetime

from core.backup_manager import BackupManager

@pytest.fixture
def backup_dir(tmp_path):
    return tmp_path / "backups"


def test_ctor_creates_directory(backup_dir):
    mgr = BackupManager(backup_dir=str(backup_dir), max_backups_per_map=3)
    assert backup_dir.exists() and backup_dir.is_dir()

def test_backup_nonexistent_map(tmp_path, backup_dir):
    mgr = BackupManager(backup_dir=str(backup_dir), max_backups_per_map=3)
    missing = tmp_path / "no_such_map.json"
    mgr.backup_map(missing)
    assert list(backup_dir.iterdir()) == []

def test_backup_map_creates_file(tmp_path, backup_dir):
    fixed = real_datetime.datetime(2021, 1, 1, 12, 34, 56)
    with patch("core.backup_manager.datetime") as mock_dt:
        mock_dt.now.return_value = fixed
        mock_dt.side_effect = lambda *a, **kw: real_datetime.datetime(*a, **kw)

        mgr = BackupManager(backup_dir=str(backup_dir), max_backups_per_map=3)
        src = tmp_path / "mymap.json"
        src.write_text("hello")

        mgr.backup_map(src)

    files = list(backup_dir.glob("mymap_*.json"))
    assert len(files) == 1

    expected = f"mymap_{fixed.strftime('%Y%m%d_%H%M%S')}.json"
    assert files[0].name == expected
    assert files[0].read_text() == "hello"

def test_prune_old_backups(tmp_path, backup_dir):
    times = [
        real_datetime.datetime(2021, 1, 1, 0, 0, 1),
        real_datetime.datetime(2021, 1, 1, 0, 0, 2),
        real_datetime.datetime(2021, 1, 1, 0, 0, 3),
        real_datetime.datetime(2021, 1, 1, 0, 0, 4),
    ]
    with patch("core.backup_manager.datetime") as mock_dt:
        mock_dt.now.side_effect = times
        mock_dt.side_effect = lambda *a, **kw: real_datetime.datetime(*a, **kw)

        mgr = BackupManager(backup_dir=str(backup_dir), max_backups_per_map=2)
        src = tmp_path / "mymap.json"
        src.write_text("x")

        for _ in range(4):
            mgr.backup_map(src)

    all_backups = sorted(backup_dir.glob("mymap_*.json"))
    assert len(all_backups) == 2

    kept_names = {p.name for p in all_backups}
    expected_names = {
        f"mymap_{real_datetime.datetime(2021, 1, 1, 0, 0, 4).strftime('%Y%m%d_%H%M%S')}.json",
        f"mymap_{real_datetime.datetime(2021, 1, 1, 0, 0, 3).strftime('%Y%m%d_%H%M%S')}.json",
    }
    assert kept_names == expected_names

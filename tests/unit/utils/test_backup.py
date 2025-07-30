import os
import shutil
import filecmp
import pytest
from utils.backup import create_backup

def test_backup_nonexistent_path(tmp_path):
    missing = tmp_path / "no_such_file.txt"
    with pytest.raises(FileNotFoundError) as exc:
        create_backup(str(missing))
    assert str(missing) in str(exc.value)

def test_backup_creates_file_and_returns_path(tmp_path, capsys):
    # create a dummy file
    orig = tmp_path / "data.txt"
    orig.write_text("hello world", encoding="utf-8")

    # call create_backup
    backup_path = create_backup(str(orig))
    # it should return the .bak path
    assert backup_path == f"{orig}.bak"

    # the backup file must now exist
    bak = tmp_path / "data.txt.bak"
    assert bak.exists()

    # contents should match
    assert filecmp.cmp(orig, bak, shallow=False)

    # print message was emitted
    captured = capsys.readouterr()
    assert f"Backup created: {bak}" in captured.out

def test_backup_overwrites_existing_backup(tmp_path):
    # create original and an existing .bak
    orig = tmp_path / "foo.txt"
    orig.write_text("first", encoding="utf-8")
    bak = tmp_path / "foo.txt.bak"
    bak.write_text("old", encoding="utf-8")

    # run backup
    result = create_backup(str(orig))
    assert result == str(bak)
    # backup file should now match orig
    assert bak.read_text(encoding="utf-8") == "first"

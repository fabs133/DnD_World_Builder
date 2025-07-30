import logging
import os
import time
from pathlib import Path
import pytest

from core.logger import AppLogger

@pytest.fixture
def create_dummy_logs(tmp_path):
    """
    Create N dummy log files in tmp_path/logs with spaced‐out mtimes.
    Returns the log directory and the list of files.
    """
    def _make(count, start_time=None):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        if start_time is None:
            # make the oldest file ~count*60s in the past
            start_time = time.time() - count * 60
        files = []
        for i in range(count):
            f = log_dir / f"log_{i}.log"
            f.write_text(f"dummy {i}")
            # space mtimes by 60s increments
            ts = start_time + i * 60
            os.utime(f, (ts, ts))
            files.append(f)
        return log_dir, files
    return _make

def test_log_dir_is_created(tmp_path):
    custom = tmp_path / "my_logs"
    assert not custom.exists()
    al = AppLogger(log_dir=str(custom), max_logs=5)
    assert custom.exists() and custom.is_dir()

def test_prune_old_logs(tmp_path, create_dummy_logs):
    # make 7 old logs; max_logs=5 => prune down to 5, then one new is created => total=6
    log_dir, old_files = create_dummy_logs(7)
    al = AppLogger(log_dir=str(log_dir), max_logs=5)

    all_logs = sorted(log_dir.glob("log_*.log"), key=lambda p: p.stat().st_mtime)
    # should end up with exactly 6 files (5 kept + 1 new)
    assert len(all_logs) == 6

    # the two oldest dummy logs (log_0.log, log_1.log) must have been pruned
    assert not (log_dir / "log_0.log").exists()
    assert not (log_dir / "log_1.log").exists()

    # the other dummy logs should still be there
    for i in range(2, 7):
        assert (log_dir / f"log_{i}.log").exists()

    # ensure exactly one “timestamped” log remains beyond the dummy ones
    timestamped = [p for p in all_logs if p.name.count("_") == 2]
    assert len(timestamped) == 1

def test_logging_writes_messages(tmp_path):
    log_dir = tmp_path / "logs2"
    al = AppLogger(log_dir=str(log_dir), max_logs=3)
    logger = al.get_logger()

    logger.info("Hello World")
    # there should be one file
    files = list(log_dir.glob("log_*.log"))
    assert len(files) == 1

    content = files[0].read_text(encoding="utf-8")
    assert "[INFO] Hello World" in content

def test_custom_log_level(tmp_path):
    log_dir = tmp_path / "logs3"
    al = AppLogger(log_dir=str(log_dir), level=logging.DEBUG, max_logs=2)
    logger = al.get_logger()

    # DEBUG should now be captured
    logger.debug("debug message")
    files = list(log_dir.glob("log_*.log"))
    assert len(files) == 1
    txt = files[0].read_text(encoding="utf-8")
    assert "[DEBUG] debug message" in txt

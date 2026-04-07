import sys
import os
import logging
import pytest
from PyQt5.QtWidgets import QApplication

@pytest.fixture(scope="session", autouse=True)
def qapp():
    return QApplication.instance() or QApplication([])


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(autouse=True)
def _reset_event_bus():
    """Reset EventBus before and after every test to prevent subscriber leakage."""
    from core.gameCreation.event_bus import EventBus
    from core.logger import app_logger

    prev_level = app_logger.level
    app_logger.setLevel(logging.CRITICAL)
    EventBus.reset()
    app_logger.setLevel(prev_level)
    yield
    app_logger.setLevel(logging.CRITICAL)
    EventBus.reset()
    app_logger.setLevel(prev_level)

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    total = terminalreporter._numcollected
    passed = len(terminalreporter.stats.get('passed', []))
    failed = len(terminalreporter.stats.get('failed', []))
    print(f"\n  Test Summary:")
    print(f"  Passed: {passed}/{total}")
    print(f"  Failed: {failed}/{total}" if failed else "  All tests passed successfully!")

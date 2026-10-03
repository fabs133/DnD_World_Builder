import sys
import os
import pytest
from PyQt5.QtWidgets import QApplication, QMessageBox

@pytest.fixture(scope="session", autouse=True)
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _fail_on_modal_message_box(monkeypatch):
    """Turn unexpected modal QMessageBox calls into immediate test failures.

    A modal dialog blocks forever in headless CI (pytest-timeout cannot
    interrupt the Qt event loop). Tests that expect a dialog should stub it
    with their own monkeypatch, which overrides this guard.
    """
    def _unexpected(*args, **kwargs):
        title, text = (list(args[1:3]) + ["", ""])[:2]
        raise AssertionError(f"Unexpected modal QMessageBox: {title!r}: {text!r}")

    for name in ("critical", "warning", "information", "question"):
        monkeypatch.setattr(QMessageBox, name, staticmethod(_unexpected))


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    total = terminalreporter._numcollected
    passed = len(terminalreporter.stats.get('passed', []))
    failed = len(terminalreporter.stats.get('failed', []))
    print(f"\n  Test Summary:")
    print(f"  Passed: {passed}/{total}")
    print(f"  Failed: {failed}/{total}" if failed else "  All tests passed successfully!")

import logging
import pytest

from models.flow.reaction.reaction_queue import ReactionQueue
from core.logger import app_logger

class DummyReaction:
    def __init__(self):
        self.resolved = False
    def resolve(self):
        self.resolved = True
    def __repr__(self):
        return "<DummyReaction>"

class ErrorReaction:
    def resolve(self):
        raise RuntimeError("fail!")

@pytest.fixture(autouse=True)
def clear_queue():
    # Ensure each test starts with an empty queue
    ReactionQueue._queue.clear()

def test_add_and_blocked_and_print(caplog):
    r = DummyReaction()
    assert not ReactionQueue.blocked()
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        ReactionQueue.add(r)
    # Should log the add message
    assert "[ReactionQueue] Added reaction:" in caplog.text
    # And now be blocked
    assert ReactionQueue.blocked()

def test_multiple_add_prints(caplog):
    r1 = DummyReaction()
    r2 = DummyReaction()
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        ReactionQueue.add(r1)
        ReactionQueue.add(r2)
    # Two occurrences of the add message
    assert caplog.text.count("[ReactionQueue] Added reaction:") == 2

def test_resolve_calls_resolve_and_prints(caplog):
    r1 = DummyReaction()
    r2 = DummyReaction()
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        ReactionQueue.add(r1)
        ReactionQueue.add(r2)
        assert ReactionQueue.blocked()

        ReactionQueue.resolve()
    # Should announce resolving and completion
    assert "[ReactionQueue] Resolving reactions..." in caplog.text
    assert "[ReactionQueue] All reactions resolved." in caplog.text

    # Queue now empty and reactions resolved
    assert not ReactionQueue.blocked()
    assert r1.resolved is True
    assert r2.resolved is True

def test_resolve_handles_exceptions_and_continues(caplog):
    bad = ErrorReaction()
    good = DummyReaction()
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        ReactionQueue.add(bad)
        ReactionQueue.add(good)

        # Should not propagate the exception
        ReactionQueue.resolve()

    # Should log an error for the bad reaction
    assert "[ReactionQueue] Error resolving" in caplog.text
    assert "fail!" in caplog.text

    # And still finish resolving
    assert "[ReactionQueue] All reactions resolved." in caplog.text
    # Good reaction must have been resolved despite the earlier error
    assert good.resolved is True

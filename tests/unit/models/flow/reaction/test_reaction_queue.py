import pytest

from models.flow.reaction.reaction_queue import ReactionQueue

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

def test_add_and_blocked_and_print(capsys):
    r = DummyReaction()
    assert not ReactionQueue.blocked()
    ReactionQueue.add(r)
    out = capsys.readouterr().out
    # Should print the add message
    assert "[ReactionQueue] Added reaction:" in out
    # And now be blocked
    assert ReactionQueue.blocked()

def test_multiple_add_prints(capsys):
    r1 = DummyReaction()
    r2 = DummyReaction()
    ReactionQueue.add(r1)
    ReactionQueue.add(r2)
    out = capsys.readouterr().out
    # Two lines starting with the add message
    assert out.count("[ReactionQueue] Added reaction:") == 2

def test_resolve_calls_resolve_and_prints(capsys):
    r1 = DummyReaction()
    r2 = DummyReaction()
    ReactionQueue.add(r1)
    ReactionQueue.add(r2)
    assert ReactionQueue.blocked()

    ReactionQueue.resolve()
    out = capsys.readouterr().out
    # Should announce resolving and completion
    assert "[ReactionQueue] Resolving reactions..." in out
    assert "[ReactionQueue] All reactions resolved." in out

    # Queue now empty and reactions resolved
    assert not ReactionQueue.blocked()
    assert r1.resolved is True
    assert r2.resolved is True

def test_resolve_handles_exceptions_and_continues(capsys):
    bad = ErrorReaction()
    good = DummyReaction()
    ReactionQueue.add(bad)
    ReactionQueue.add(good)

    # Should not propagate the exception
    ReactionQueue.resolve()
    out = capsys.readouterr().out

    # Should print an error for the bad reaction
    assert "[ReactionQueue] Error resolving" in out
    assert "fail!" in out

    # And still finish resolving
    assert "[ReactionQueue] All reactions resolved." in out
    # Good reaction must have been resolved despite the earlier error
    assert good.resolved is True

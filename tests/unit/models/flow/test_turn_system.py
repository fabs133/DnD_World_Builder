import pytest
from models.flow.turn_system import TurnSystem
from core.gameCreation.event_bus import EventBus    # your EventBus :contentReference[oaicite:0]{index=0}:contentReference[oaicite:1]{index=1}
from models.flow.action.action_validator import ActionValidator
from models.flow.reaction.reaction_queue import ReactionQueue


class DummyEntity:
    def __init__(self, name):
        self.name = name
    def decide_action(self):
        # return a dummy action with execute()
        action = type("A", (), {"execute_called": False, "execute": lambda self: setattr(self, "execute_called", True)})()
        return action

@pytest.fixture(autouse=True)
def reset_eventbus(monkeypatch):
    """Monkeypatch EventBus.emit so we capture events in a list."""
    emits = []
    monkeypatch.setattr(EventBus, "emit",
                        classmethod(lambda cls, et, data: emits.append((et, data))))
    return emits

def test_schedule_and_start_round(capsys):
    ts = TurnSystem([])
    called = []
    ts.schedule_in(0, lambda d: called.append(("now", d)), data=1)
    ts.schedule_in(1, lambda d: called.append(("next", d)), data=2)

    # At round 1 start we fire the 0‐delay only
    ts.start_round()
    out = capsys.readouterr().out.strip()
    assert out == "Round 1 starts!"
    assert called == [("now", 1)]
    # One remains for round 2
    assert len(ts._scheduled) == 1
    assert ts._scheduled[0][0] == 2 and ts._scheduled[0][2] == 2

    # Now start round 2
    ts.start_round()
    assert ("next", 2) in called

def test_next_turn_cycles_and_prints(capsys):
    e1, e2, e3 = DummyEntity("E1"), DummyEntity("E2"), DummyEntity("E3")
    ts = TurnSystem([e1, e2, e3])
    ts.next_turn()
    assert capsys.readouterr().out.strip() == "It is now E2's turn."
    ts.next_turn()
    assert capsys.readouterr().out.strip() == "It is now E3's turn."
    ts.next_turn()
    assert capsys.readouterr().out.strip() == "It is now E1's turn."

def test_execute_turn_not_blocked(monkeypatch, reset_eventbus, capsys):
    p1 = DummyEntity("P1")
    p2 = DummyEntity("P2")
    ts = TurnSystem([p1, p2])

    # Always valid
    monkeypatch.setattr(ActionValidator, "validate", staticmethod(lambda _: True))
    # No reactions blocking
    monkeypatch.setattr(ReactionQueue, "blocked", staticmethod(lambda: False))
    did_resolve = {"called": False}
    monkeypatch.setattr(ReactionQueue, "resolve",
                        staticmethod(lambda: did_resolve.update(called=True)))

    # Stub decide_action and make sure execute() is called
    action = p1.decide_action()
    p1.decide_action = lambda: action

    ts.current_turn = 0
    ts.round_number = 1
    ts.execute_turn()

    evts = reset_eventbus
    assert ("ACTION_PROPOSED", action) in evts
    assert ("ACTION_EXECUTED", action) in evts
    assert action.execute_called is True
    assert did_resolve["called"] is False

    out = capsys.readouterr().out
    assert "P1's turn ends." in out
    assert "It is now P2's turn." in out

def test_execute_turn_blocked(monkeypatch, reset_eventbus):
    p = DummyEntity("Px")
    ts = TurnSystem([p])

    monkeypatch.setattr(ActionValidator, "validate", staticmethod(lambda a: True))
    monkeypatch.setattr(ReactionQueue, "blocked", staticmethod(lambda: True))
    did_resolve = {"called": False}
    monkeypatch.setattr(ReactionQueue, "resolve",
                        staticmethod(lambda: did_resolve.update(called=True)))

    # This action’s execute would blow up if called
    bad_action = type("A", (), {"execute": lambda self: (_ for _ in ()).throw(Exception("should not run"))})()
    p.decide_action = lambda: bad_action

    ts.current_turn = 0
    ts.round_number = 1
    # Should not raise
    ts.execute_turn()

    evts = reset_eventbus
    assert ("ACTION_PROPOSED", bad_action) in evts
    assert not any(evt == "ACTION_EXECUTED" for evt, _ in evts)
    assert did_resolve["called"] is True

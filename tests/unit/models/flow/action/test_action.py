import re
import pytest

import models.flow.action.action as action_mod
from models.flow.action.action import Action

class DummyAction(Action):
    def validate(self, game_state=None):
        return True
    def execute(self, game_state=None):
        pass

def test_interrupt_marks_blocked_and_logs():
    act = DummyAction(actor="Tester")
    assert act.blocked is False
    assert act.execution_log == []

    act.interrupt("hit by rock")
    assert act.blocked is True
    assert "Action interrupted: hit by rock" in act.execution_log

def test_roll_valid_expression(monkeypatch, capsys):
    # stub out random.randint to always return 1
    monkeypatch.setattr(action_mod.random, "randint", lambda a, b: 1)

    # 2d6+3 → rolls [1,1] + 3 = 5
    total = Action.roll("2d6+3")
    captured = capsys.readouterr().out.strip()
    assert total == 5
    # message includes the exact list and modifier
    assert re.search(r"Rolling 2d6\+3: \[1, 1\] \+ 3 = 5", captured)

    # implicit 1d8 (no leading number) and negative modifier
    monkeypatch.setattr(action_mod.random, "randint", lambda a, b: 4)
    total2 = Action.roll("d8-2")
    out2 = capsys.readouterr().out
    # 4 + (-2) = 2
    assert total2 == 2
    assert "Rolling d8-2: [4] + -2 = 2" in out2

def test_roll_invalid_expression_raises():
    with pytest.raises(ValueError) as ei:
        Action.roll("no dice here")
    msg = str(ei.value)
    assert "Invalid dice expression" in msg

def test_apply_effect_adds_to_target_and_prints(capsys):
    class Target:
        def __init__(self):
            self.name = "Enemy"
    tgt = Target()

    effect = {"type": "buff", "details": "advantage on rolls", "duration": 2}
    # Call as a classmethod-style function
    Action.apply_effect(tgt, effect)

    # Target should have active_effects list
    assert hasattr(tgt, "active_effects")
    assert isinstance(tgt.active_effects, list)
    assert tgt.active_effects == [effect]  # exact dict appended

    out = capsys.readouterr().out.strip()
    assert out == "Enemy gains effect: buff (advantage on rolls) for 2 rounds."

def test_apply_effect_defaults(monkeypatch, capsys):
    class T:
        def __init__(self):
            self.name = "Hero"
    t = T()

    # missing details and duration
    Action.apply_effect(t, {"type": "stun"})
    assert t.active_effects[-1] == {
        "type": "stun", "details": "", "duration": 1
    }
    printed = capsys.readouterr().out
    assert printed.strip() == "Hero gains effect: stun () for 1 rounds."

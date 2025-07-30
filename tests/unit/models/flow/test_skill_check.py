import pytest
from models.flow.skill_check import SkillCheck


def test_attempt_success_no_advantage():
    check = SkillCheck("Perception", dc=10)
    result = check.attempt({"Perception": 20}, advantage=False)
    assert result is True  # guaranteed due to modifier


def test_attempt_fail_no_stat():
    check = SkillCheck("Stealth", dc=15)
    # Without skill, modifier is 0 and dice roll max is 20
    for _ in range(10):
        result = check.attempt({}, advantage=False)
        assert isinstance(result, bool)


def test_attempt_with_advantage(monkeypatch):
    check = SkillCheck("Arcana", dc=10)

    rolls = [5, 17]
    monkeypatch.setattr("random.randint", lambda a, b: rolls.pop())

    result = check.attempt({"Arcana": 0}, advantage=True)
    assert result is True  # higher roll is 17


def test_attempt_with_disadvantage(monkeypatch):
    check = SkillCheck("Survival", dc=10)

    rolls = [18, 3]
    monkeypatch.setattr("random.randint", lambda a, b: rolls.pop())

    result = check.attempt({"Survival": 0}, disadvantage=True)
    assert result is False  # lower roll is 3


def test_auto_pass():
    check = SkillCheck("History", dc=100, auto_pass=True)
    assert check.attempt({"History": -100}) is True


def test_auto_fail():
    check = SkillCheck("Deception", dc=1, auto_fail=True)
    assert check.attempt({"Deception": 100}) is False


def test_zero_modifier_edge_case(monkeypatch):
    monkeypatch.setattr("random.randint", lambda a, b: 10)
    check = SkillCheck("Insight", dc=10)
    assert check.attempt({"Insight": 0}) is True  # 10+0 meets DC

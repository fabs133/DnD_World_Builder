import pytest
from models.flow.condition.condition_list import AlwaysTrue, PerceptionCheck


def test_always_true():
    cond = AlwaysTrue()
    assert cond({}) is True
    assert cond({"any": "data"}) is True


def test_perception_check_pass():
    cond = PerceptionCheck(dc=12)
    assert cond({"perception": 15}) is True


def test_perception_check_fail():
    cond = PerceptionCheck(dc=18)
    assert cond({"perception": 10}) is False


def test_perception_check_missing_key():
    cond = PerceptionCheck(dc=5)
    assert cond({}) is False


def test_perception_check_invalid_type(capfd):
    cond = PerceptionCheck(dc=5)
    assert cond({"perception": "bad"}) is False

    captured = capfd.readouterr()
    assert "invalid perception" in captured.out.lower()

def test_always_true_serialization_roundtrip():
    original = AlwaysTrue()
    data = original.to_dict()
    loaded = AlwaysTrue.from_dict(data)
    assert isinstance(loaded, AlwaysTrue)


def test_perception_check_serialization_roundtrip():
    original = PerceptionCheck(dc=13)
    data = original.to_dict()
    loaded = PerceptionCheck.from_dict(data)
    assert isinstance(loaded, PerceptionCheck)
    assert loaded.dc == 13

import pytest

@pytest.mark.parametrize("dc,perception,expected", [
    (10, 15, True),
    (18, 10, False),
    (5, None, False),
    (5, "bad", False),
])
def test_perception_check_various(dc, perception, expected, capfd):
    cond = PerceptionCheck(dc=dc)
    result = cond({"perception": perception})
    assert result is expected

    if isinstance(perception, str) or perception is None:
        captured = capfd.readouterr()
        assert "invalid perception" in captured.out.lower()

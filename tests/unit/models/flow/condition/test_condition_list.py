import logging
import pytest

from models.flow.condition.condition_list import AlwaysTrue, PerceptionCheck
from core.logger import app_logger

def test_always_true_behavior_and_dict():
    at = AlwaysTrue()
    # __call__ always returns True
    assert at({}) is True
    assert at({"anything": 123}) is True

    # to_dict
    d = at.to_dict()
    assert isinstance(d, dict)
    assert d == {"type": "AlwaysTrue"}

    # from_dict
    at2 = AlwaysTrue.from_dict({"type": "AlwaysTrue"})
    assert isinstance(at2, AlwaysTrue)
    assert at2({}) is True

@pytest.mark.parametrize("dc,perception,expected", [
    (5, "6", True),      # string parses
    (5, 5, True),        # integer equal
    (5, 4, False),       # below DC
    (0, None, False),    # None treated as invalid → caught, False
    (0, "0", True),      # 0 >= 0
    (3, {}, False),      # missing or bad → default 0 < 3
])
def test_perception_check_valid_and_invalid(dc, perception, expected, caplog):
    pc = PerceptionCheck(dc)
    # build event_data dict only if perception is not dict
    event_data = {}
    if perception is not {}:
        event_data = {"perception": perception}
    else:
        event_data = {}  # simulate missing key
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        result = pc(event_data)
    if perception is None:
        # None → int(None) raises TypeError → logs warning, returns False
        assert "Invalid perception value" in caplog.text
        assert result is False
    else:
        # for valid parsing or missing default
        assert result is expected

def test_perception_check_to_dict_and_from_dict():
    pc = PerceptionCheck(7)
    d = pc.to_dict()
    assert d == {"type": "PerceptionCheck", "dc": 7}

    pc2 = PerceptionCheck.from_dict({"type": "PerceptionCheck", "dc": 12})
    assert isinstance(pc2, PerceptionCheck)
    assert pc2.dc == 12
    # ensure it works
    assert pc2({"perception": 15}) is True
    assert pc2({"perception": 5}) is False

def test_perception_non_numeric_string(caplog):
    pc = PerceptionCheck(2)
    # non-numeric string → ValueError → caught, logs, returns False
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        res = pc({"perception": "not-a-number"})
    assert res is False
    assert "Invalid perception value in" in caplog.text

import logging
import pytest
from models.flow.condition.condition_list import AlwaysTrue, PerceptionCheck
from core.logger import app_logger


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


def test_perception_check_invalid_type(caplog):
    cond = PerceptionCheck(dc=5)
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        assert cond({"perception": "bad"}) is False

    assert "invalid perception" in caplog.text.lower()

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
def test_perception_check_various(dc, perception, expected, caplog):
    cond = PerceptionCheck(dc=dc)
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        result = cond({"perception": perception})
    assert result is expected

    if isinstance(perception, str) or perception is None:
        assert "invalid perception" in caplog.text.lower()

import logging
import pytest
from models.flow.reaction.reactions_list import ApplyDamage, AlertGamemaster
from core.logger import app_logger


class DummyTarget:
    def __init__(self):
        self.damage_log = []

    def take_damage(self, amount, damage_type):
        self.damage_log.append((damage_type, amount))


def test_apply_damage_reduces_hp():
    target = DummyTarget()
    reaction = ApplyDamage(damage_type="fire", amount=10)

    event_data = {"target": target}
    reaction(event_data)

    assert ("fire", 10) in target.damage_log


def test_apply_damage_no_target(caplog):
    reaction = ApplyDamage(damage_type="cold", amount=5)
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        reaction({})  # No target

    assert "missing target" in caplog.text.lower()



def test_apply_damage_serialization_roundtrip():
    original = ApplyDamage("necrotic", 12)
    data = original.to_dict()
    loaded = ApplyDamage.from_dict(data)

    assert loaded.damage_type == "necrotic"
    assert loaded.amount == 12


def test_alert_gamemaster_prints_message(caplog):
    msg = "A trap was triggered!"
    reaction = AlertGamemaster(message=msg)

    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        reaction({})  # No need for real data yet
    assert msg in caplog.text


def test_alert_gamemaster_serialization_roundtrip():
    original = AlertGamemaster("Danger ahead")
    data = original.to_dict()
    loaded = AlertGamemaster.from_dict(data)

    assert loaded.message == "Danger ahead"

def test_apply_damage_target_wrong_type(caplog):
    reaction = ApplyDamage("acid", 8)
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        reaction({"target": "not a GameEntity"})

    assert "missing target" in caplog.text.lower()

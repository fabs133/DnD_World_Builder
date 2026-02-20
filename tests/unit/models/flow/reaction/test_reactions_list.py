import logging
import pytest

from models.flow.reaction.reactions_list import ApplyDamage, AlertGamemaster
from core.logger import app_logger

class DummyTarget:
    def __init__(self):
        self.damage_calls = []
    def take_damage(self, amount, damage_type):
        self.damage_calls.append((amount, damage_type))

class DummyGame:
    def __init__(self):
        self.events = []
    def flag_event(self, msg):
        self.events.append(msg)

def test_apply_damage_calls_target_take_damage():
    dmg = ApplyDamage("piercing", 7)
    tgt = DummyTarget()
    event = {"target": tgt}

    dmg(event)
    assert tgt.damage_calls == [(7, "piercing")]

def test_apply_damage_missing_or_invalid_target_prints(caplog):
    dmg = ApplyDamage("fire", 3)
    # No 'target' key
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        dmg({})
    assert "[ApplyDamage] Invalid or missing target in event_data" in caplog.text

    caplog.clear()
    # target without take_damage
    class Bad:
        pass
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        dmg({"target": Bad()})
    assert "[ApplyDamage] Invalid or missing target in event_data" in caplog.text

def test_apply_damage_dict_roundtrip():
    orig = ApplyDamage("cold", 5)
    d = orig.to_dict()
    assert d == {"type": "ApplyDamage", "damage_type": "cold", "amount": 5}

    recons = ApplyDamage.from_dict(d)
    assert isinstance(recons, ApplyDamage)
    # same attributes
    assert recons.damage_type == "cold"
    assert recons.amount == 5

def test_alert_gamemaster_prints_and_flags(caplog):
    msg = "Watch out!"
    alert = AlertGamemaster(msg)
    game = DummyGame()
    event = {"game": game}

    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        alert(event)
    # Logged GM alert
    assert f"[GM ALERT] {msg}" in caplog.text
    # Game.flag_event called
    assert game.events == [msg]

def test_alert_gamemaster_without_game_or_flag(caplog):
    msg = "Heads up"
    alert = AlertGamemaster(msg)

    # No game key
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        alert({})
    assert f"[GM ALERT] {msg}" in caplog.text

    caplog.clear()
    # game without flag_event
    class NoFlag:
        pass
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        alert({"game": NoFlag()})
    assert f"[GM ALERT] {msg}" in caplog.text

def test_alert_gamemaster_dict_roundtrip():
    orig = AlertGamemaster("Alert!")
    d = orig.to_dict()
    assert d == {"type": "AlertGamemaster", "message": "Alert!"}

    recon = AlertGamemaster.from_dict(d)
    assert isinstance(recon, AlertGamemaster)
    assert recon.message == "Alert!"

import logging
import pytest

from models.flow.reaction.reaction import Reaction
from core.logger import app_logger

class DummyReactor:
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return f"<DummyReactor {self.name}>"

class DummyAction:
    def __str__(self):
        return "ActionX"
    def __repr__(self):
        return "<DummyAction>"

def test_reaction_attributes():
    reactor = DummyReactor("R1")
    action = DummyAction()
    rx = Reaction(reactor, action)
    # Attributes wired correctly
    assert rx.reactor is reactor
    assert rx.trigger_action is action

def test_resolve_prints_with_string_action(caplog):
    reactor = DummyReactor("Ally")
    action = "Attack"
    rx = Reaction(reactor, action)
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        rx.resolve()
    assert "Ally reacts to Attack!" in caplog.text

def test_resolve_uses_str_of_action(caplog):
    reactor = DummyReactor("Mage")
    action = DummyAction()
    rx = Reaction(reactor, action)
    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        rx.resolve()
    # Should use action.__str__()
    assert "Mage reacts to ActionX!" in caplog.text

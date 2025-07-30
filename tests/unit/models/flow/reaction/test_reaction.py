import pytest

from models.flow.reaction.reaction import Reaction

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

def test_resolve_prints_with_string_action(capsys):
    reactor = DummyReactor("Ally")
    action = "Attack"
    rx = Reaction(reactor, action)
    rx.resolve()
    out = capsys.readouterr().out.strip()
    assert out == "Ally reacts to Attack!"

def test_resolve_uses_str_of_action(capsys):
    reactor = DummyReactor("Mage")
    action = DummyAction()
    rx = Reaction(reactor, action)
    rx.resolve()
    out = capsys.readouterr().out.strip()
    # Should use action.__str__()
    assert out == "Mage reacts to ActionX!"

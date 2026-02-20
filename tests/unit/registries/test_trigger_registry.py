import logging
import pytest
from core.gameCreation.trigger import Trigger
from core.logger import app_logger
from models.flow.reaction.reactions_list import ApplyDamage
from models.flow.condition.condition_list import AlwaysTrue
from registries.trigger_registry import TriggerRegistry, global_trigger_registry

def make_simple_trigger():
    # event_type, condition, reaction
    return Trigger("EVT", AlwaysTrue, ApplyDamage("fire", 2))

def test_register_and_is_registered_and_get_source():
    reg = TriggerRegistry()
    trig = make_simple_trigger()

    # initially not registered
    assert not reg.is_registered(trig)
    # add it
    added = reg.add_trigger(trig, source="TestSource")
    assert added is True
    assert reg.is_registered(trig)
    # source recorded
    assert reg.get_source(trig) == "TestSource"

    # adding again returns False, state unchanged
    added2 = reg.add_trigger(trig, source="Other")
    assert added2 is False
    assert reg.get_source(trig) == "TestSource"

def test_remove_trigger():
    reg = TriggerRegistry()
    trig = make_simple_trigger()
    reg.add_trigger(trig, source="S")
    assert reg.is_registered(trig)
    reg.remove_trigger(trig)
    assert not reg.is_registered(trig)
    # source falls back to "unknown"
    assert reg.get_source(trig) == "unknown"

def test_get_all_and_by_source():
    reg = TriggerRegistry()
    t1 = Trigger("A", AlwaysTrue, None)
    t2 = Trigger("B", AlwaysTrue, None)
    reg.add_trigger(t1, source="X")
    reg.add_trigger(t2, source="Y")
    alls = reg.get_all_triggers()
    assert set(alls) == {t1, t2}

    by_x = reg.get_triggers_by_source("X")
    assert by_x == [t1]
    by_unknown = reg.get_triggers_by_source("Z")
    assert by_unknown == []

def test_register_and_get_function():
    reg = TriggerRegistry()

    def foo(): pass
    reg.register_function(foo)
    # key is function name
    assert reg.get_function("foo") is foo

    def bar(): pass
    reg.register_function(bar, name="baz")
    assert reg.get_function("baz") is bar

def test_debug_print(caplog):
    reg = TriggerRegistry()
    t1 = Trigger("E1", AlwaysTrue, None)
    t2 = Trigger("E2", AlwaysTrue, None)
    reg.add_trigger(t1, source="S1")
    reg.add_trigger(t2)  # no source => unknown

    with caplog.at_level(logging.DEBUG, logger=app_logger.name):
        reg.debug_print()
    lines = caplog.text.strip().splitlines()
    # First line header
    assert any("TriggerRegistry:" in line for line in lines)
    # Should print each trigger with its repr and source
    assert any("E1" in line and "from: S1" in line for line in lines)
    assert any("E2" in line and "from: unknown" in line for line in lines)

def test_global_registry_is_separate_instance():
    # Clear any existing triggers
    global_trigger_registry._triggers.clear()
    # Add one
    gt = make_simple_trigger()
    global_trigger_registry.add_trigger(gt, source="G")
    assert global_trigger_registry.is_registered(gt)
    # It should not affect a new registry
    newr = TriggerRegistry()
    assert not newr.is_registered(gt)

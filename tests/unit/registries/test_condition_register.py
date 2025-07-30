import pytest

from models.flow.condition.condition_list import AlwaysTrue, PerceptionCheck
from registries.condition_registry import ConditionRegistry, condition_registry

def test_manual_register_and_get_class():
    reg = ConditionRegistry()
    # Initially empty
    assert reg.get_all() == []
    # Register a new dummy class
    class Dummy:
        @classmethod
        def from_dict(cls, data):
            return "ok"
    reg.register("Dummy", Dummy)
    assert reg.get_class("Dummy") is Dummy
    assert "Dummy" in reg.get_all()

def test_create_known_types():
    data_at = {"type": "AlwaysTrue"}
    at = condition_registry.create(data_at)
    assert isinstance(at, AlwaysTrue)
    # PerceptionCheck via dict
    data_pc = {"type": "PerceptionCheck", "dc": 3}
    pc = condition_registry.create(data_pc)
    assert isinstance(pc, PerceptionCheck)
    assert pc.dc == 3

def test_create_unknown_raises():
    bad = {"type": "DoesNotExist"}
    with pytest.raises(ValueError) as ei:
        condition_registry.create(bad)
    assert "Unknown type: DoesNotExist" in str(ei.value)

def test_list_keys_and_aliases():
    keys = condition_registry.get_all()
    assert "AlwaysTrue" in keys
    assert "PerceptionCheck" in keys
    # list_keys is alias to get_all
    assert set(condition_registry.list_keys()) == set(keys)

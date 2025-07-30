import pytest
from core.gameCreation.trigger import Trigger
from models.flow.condition.condition_list import AlwaysTrue

class DummyTurnManager:
    def __init__(self):
        self.current_turn = 0
    def next_turn(self):
        self.current_turn += 1

class DummyWorld:
    def __init__(self):
        self.turn_manager = DummyTurnManager()

@pytest.fixture
def dummy_world():
    return DummyWorld()


def test_trigger_cooldown_blocks_and_allows(dummy_world):
    world = dummy_world
    calls = []
    def reaction(data):
        # record the turn number when reaction is executed
        calls.append(world.turn_manager.current_turn)

    # cooldown of 2 turns
    trig = Trigger(
        event_type="SPELL_CAST",
        condition=AlwaysTrue(),
        reaction=reaction,
        cooldown=2
    )
    event_data = {"world": world}

    # Turn 0: first fire should execute
    trig.check_and_react(event_data)
    assert calls == [0]

    # Same turn: within cooldown, should not execute again
    trig.check_and_react(event_data)
    assert calls == [0]

    # Advance to turn 1: still within cooldown (1 - 0 < 2)
    world.turn_manager.next_turn()
    trig.check_and_react(event_data)
    assert calls == [0]

    # Advance to turn 2: cooldown expired (2 - 0 >= 2), should execute
    world.turn_manager.next_turn()
    trig.check_and_react(event_data)
    assert calls == [0, 2]

    # Advance to turn 3: now last fired at 2, 3 - 2 < 2, should skip
    world.turn_manager.next_turn()
    trig.check_and_react(event_data)
    assert calls == [0, 2]

    # Advance to turn 4: 4 - 2 >= 2, should execute again
    world.turn_manager.next_turn()
    trig.check_and_react(event_data)
    assert calls == [0, 2, 4]

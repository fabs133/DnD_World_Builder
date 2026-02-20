import pytest
from core.gameCreation.event_bus import EventBus

# --- Test Setup ---

@pytest.fixture(autouse=True)
def reset_event_bus():
    """Ensure a clean EventBus state before each test."""
    EventBus.reset()


# --- Tests ---

def test_subscribe_and_emit(monkeypatch):
    called = {}

    def sample_handler(data):
        called["data"] = data

    EventBus.subscribe("PLAYER_MOVE", sample_handler)
    EventBus.emit("PLAYER_MOVE", {"x": 1, "y": 2})

    assert called["data"] == {"x": 1, "y": 2}


def test_emit_with_no_subscribers():
    # Should not raise or log errors
    EventBus.emit("NO_LISTENERS", {"irrelevant": True})


def test_duplicate_subscription():
    handler = lambda data: None
    EventBus.subscribe("DUPLICATE_TEST", handler)
    EventBus.subscribe("DUPLICATE_TEST", handler)

    inst = EventBus._get_instance()
    assert inst._subscribers["DUPLICATE_TEST"].count(handler) == 1


def test_unsubscribe_successful():
    called = []

    def handler(data):
        called.append("hit")

    EventBus.subscribe("ACTION", handler)
    EventBus.unsubscribe("ACTION", handler)
    EventBus.emit("ACTION", {"run": True})

    assert not called


def test_unsubscribe_missing_handler():
    # Should not raise
    EventBus.unsubscribe("NON_EXISTENT", lambda _: None)


def test_reset_clears_all():
    EventBus.subscribe("A", lambda _: None)
    EventBus.subscribe("B", lambda _: None)
    EventBus.reset()

    inst = EventBus._get_instance()
    assert inst._subscribers == {}

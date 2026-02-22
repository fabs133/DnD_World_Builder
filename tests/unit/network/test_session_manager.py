"""Tests for SessionManager using InMemory transport."""
import asyncio
import time
import pytest
from PyQt5.QtWidgets import QApplication
from network.session_manager import SessionManager
from network.transport import InMemoryServer, InMemoryClient
from models.game_master import Gamemaster
from models.entities.game_entity import GameEntity


def _wait_for_signals(seconds=0.5, steps=10):
    """Sleep while processing Qt events so cross-thread signals are delivered."""
    for _ in range(steps):
        time.sleep(seconds / steps)
        QApplication.processEvents()


@pytest.fixture
def gamemaster():
    gm = Gamemaster()
    gm.add_entity(GameEntity("Hero", "player", stats={"hp": 20}))
    gm.add_entity(GameEntity("Goblin", "enemy", stats={"hp": 5}))
    return gm


class TestSessionManagerHost:

    def test_host_starts_and_stops(self, gamemaster):
        """SessionManager can start and stop hosting with InMemory transport."""
        server = InMemoryServer()

        sm = SessionManager(
            gamemaster=gamemaster,
            transport_factory=lambda port=None: server,
        )

        sm.host(port=9999)
        _wait_for_signals(0.3)
        assert sm.is_hosting

        sm.stop_hosting()
        assert not sm.is_hosting

    def test_host_creates_session(self, gamemaster):
        """Hosting creates a SessionHost that accepts connections."""
        server = InMemoryServer()

        sm = SessionManager(
            gamemaster=gamemaster,
            transport_factory=lambda port=None: server,
        )

        sm.host(port=9999)
        _wait_for_signals(0.3)

        assert sm._host is not None
        assert sm._host.session_id is not None

        sm.stop_hosting()

    def test_host_event_bridge_started(self, gamemaster):
        """Hosting starts the EventBridge and TurnBridge."""
        server = InMemoryServer()

        sm = SessionManager(
            gamemaster=gamemaster,
            transport_factory=lambda port=None: server,
        )

        sm.host(port=9999)
        _wait_for_signals(0.3)

        assert sm._event_bridge is not None
        assert sm._turn_bridge is not None

        sm.stop_hosting()

        # After stop, bridges should be cleaned up
        assert sm._event_bridge is None
        assert sm._turn_bridge is None


class TestSessionManagerJoin:

    def test_join_connects_client(self, gamemaster):
        """SessionManager can join a hosted session via InMemory transport."""
        server = InMemoryServer()

        # Host
        host_sm = SessionManager(
            gamemaster=gamemaster,
            transport_factory=lambda port=None: server,
        )
        host_sm.host(port=9999)
        _wait_for_signals(0.3)

        # Client
        client_sm = SessionManager(
            transport_factory=lambda host=None, port=None: InMemoryClient(server),
        )

        connected_signals = []
        client_sm.signals.connected.connect(lambda: connected_signals.append(True))

        client_sm.join("localhost", 9999, "Alice")
        _wait_for_signals(0.8)

        assert client_sm.is_connected
        assert len(connected_signals) == 1

        client_sm.leave()
        host_sm.stop_hosting()

    def test_chat_signal_wiring(self, gamemaster):
        """The _on_chat callback correctly emits the chat_received signal."""
        sm = SessionManager(gamemaster=gamemaster)

        chat_received = []
        sm.signals.chat_received.connect(
            lambda sender, msg: chat_received.append((sender, msg))
        )

        # Simulate a CHAT message arriving
        from network.protocol import Message, MessageType
        fake_msg = Message(
            type=MessageType.CHAT,
            payload={"sender": "Alice", "message": "Hello!"},
        )
        sm._on_chat(fake_msg)

        _wait_for_signals(0.2)

        assert len(chat_received) == 1
        assert chat_received[0] == ("Alice", "Hello!")


class TestSessionManagerSignals:

    def test_disconnected_signal_on_stop(self, gamemaster):
        """The disconnected signal fires when hosting stops."""
        server = InMemoryServer()

        sm = SessionManager(
            gamemaster=gamemaster,
            transport_factory=lambda port=None: server,
        )

        disconnected = []
        sm.signals.disconnected.connect(lambda: disconnected.append(True))

        sm.host(port=9999)
        _wait_for_signals(0.3)

        sm.stop_hosting()
        _wait_for_signals(0.2)
        assert len(disconnected) >= 1

    def test_double_host_ignored(self, gamemaster):
        """Calling host() twice doesn't create two sessions."""
        server = InMemoryServer()

        sm = SessionManager(
            gamemaster=gamemaster,
            transport_factory=lambda port=None: server,
        )

        sm.host(port=9999)
        _wait_for_signals(0.3)

        sm.host(port=9998)  # Should be ignored
        _wait_for_signals(0.1)

        assert sm.is_hosting

        sm.stop_hosting()

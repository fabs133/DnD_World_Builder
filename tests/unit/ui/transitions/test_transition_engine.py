"""Tests for TransitionEngine."""

import pytest
from unittest.mock import MagicMock
from PyQt5.QtWidgets import QWidget

from ui.transitions.transition_engine import TransitionEngine


@pytest.fixture
def parent(qapp):
    w = QWidget()
    w.resize(800, 600)
    return w


@pytest.fixture
def engine(parent):
    return TransitionEngine(parent)


class TestCutTransition:

    def test_cut_hides_outgoing_shows_incoming(self, engine, parent):
        parent.show()
        outgoing = QWidget(parent)
        incoming = QWidget(parent)
        outgoing.show()

        engine.execute("launcher_to_overview", outgoing=outgoing, incoming=incoming)

        assert outgoing.isHidden()
        assert incoming.isVisible()

    def test_cut_no_outgoing(self, engine, parent):
        parent.show()
        incoming = QWidget(parent)

        engine.execute("launcher_to_overview", incoming=incoming)
        assert incoming.isVisible()


class TestFadeTransition:

    def test_fade_incoming_only(self, engine, parent):
        parent.show()
        incoming = QWidget(parent)
        completed = []
        engine.transition_completed.connect(lambda tid: completed.append(tid))

        engine.execute("overview_to_editor", incoming=incoming)

        # Incoming should be shown (animation starts immediately)
        assert incoming.isVisible()


class TestSignals:

    def test_transition_started_emitted(self, engine, parent):
        started = []
        engine.transition_started.connect(lambda tid: started.append(tid))

        engine.execute("launcher_to_overview")

        assert len(started) == 1
        assert started[0] == "launcher_to_overview"

    def test_transition_completed_emitted_for_cut(self, engine, parent):
        completed = []
        engine.transition_completed.connect(lambda tid: completed.append(tid))

        engine.execute("launcher_to_overview")

        assert len(completed) == 1

    def test_on_complete_callback(self, engine, parent):
        callback = MagicMock()
        engine.execute("launcher_to_overview", on_complete=callback)
        callback.assert_called_once()


class TestSoundIntegration:

    def test_plays_sound_when_manager_provided(self, parent):
        sound = MagicMock()
        engine = TransitionEngine(parent, sound_manager=sound)

        engine.execute("overview_to_editor")

        sound.play.assert_called_once()

    def test_no_crash_without_sound_manager(self, engine, parent):
        # Should not raise
        engine.execute("overview_to_editor")


class TestUnknownTransition:

    def test_unknown_id_does_not_crash(self, engine, parent):
        callback = MagicMock()
        engine.execute("totally_unknown_transition", on_complete=callback)
        callback.assert_called_once()


class TestCinematicTransition:

    def test_cinematic_hides_outgoing(self, engine, parent):
        parent.show()
        outgoing = QWidget(parent)
        outgoing.show()

        engine.execute("exploration_to_combat", outgoing=outgoing)

        assert not outgoing.isVisible()

    def test_cinematic_with_theme_engine(self, parent):
        theme = MagicMock()
        engine = TransitionEngine(parent, theme_engine=theme)

        incoming = QWidget(parent)
        engine.execute("exploration_to_combat", incoming=incoming)

        # Theme swap happens after hold timer — can't assert synchronously
        # But the engine should not crash

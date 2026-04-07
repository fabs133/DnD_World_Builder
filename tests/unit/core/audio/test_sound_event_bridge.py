"""Tests for SoundEventBridge."""

import pytest
from unittest.mock import MagicMock, call

from core.events import (
    COMBAT_ENDED, COMBAT_STARTED, ENTITY_DAMAGED, ENTITY_DIED,
    INITIATIVE_ROLLED, ROUND_STARTED, TURN_STARTED,
)
from core.gameCreation.event_bus import EventBus
from core.audio.sound_event_bridge import SoundEventBridge
from core.audio.ui_sound_manager import SoundCategory


@pytest.fixture(autouse=True)
def reset_bus():
    EventBus.reset()
    yield
    EventBus.reset()


@pytest.fixture
def sound():
    mock = MagicMock()
    # resolve_path returns None so fallback sounds are used in tests
    mock.resolve_path.return_value = None
    return mock


@pytest.fixture
def bridge(sound):
    b = SoundEventBridge(sound, viewer_entity_name="Hero")
    b.start()
    yield b
    b.stop()


class TestAlwaysPlayEvents:

    def test_combat_started(self, bridge, sound):
        EventBus.emit(COMBAT_STARTED, {})
        sound.play_shared.assert_called_with("combat_start", SoundCategory.ALERT)

    def test_victory(self, bridge, sound):
        EventBus.emit(COMBAT_ENDED, {"outcome": "victory"})
        sound.play_shared.assert_called_with("victory", SoundCategory.ALERT)

    def test_defeat(self, bridge, sound):
        EventBus.emit(COMBAT_ENDED, {"outcome": "defeat"})
        sound.play_shared.assert_called_with("defeat", SoundCategory.ALERT)

    def test_initiative(self, bridge, sound):
        EventBus.emit(INITIATIVE_ROLLED, {})
        sound.play_shared.assert_called_with("initiative", SoundCategory.COMBAT)

    def test_round_bell(self, bridge, sound):
        EventBus.emit(ROUND_STARTED, {"round": 2})
        sound.play_shared.assert_called_with("round_bell", SoundCategory.COMBAT)

    def test_entity_died(self, bridge, sound):
        EventBus.emit(ENTITY_DIED, {"entity": "Goblin"})
        sound.play.assert_called_with("enemy_down", SoundCategory.COMBAT)


class TestLocalPlayerOnly:

    def test_turn_started_local(self, bridge, sound):
        EventBus.emit(TURN_STARTED, {"entity": "Hero", "round": 1})
        sound.play_shared.assert_any_call("your_turn", SoundCategory.ALERT)

    def test_turn_started_not_local(self, bridge, sound):
        sound.reset_mock()
        EventBus.emit(TURN_STARTED, {"entity": "Goblin", "round": 1})
        # Should NOT play your_turn for non-local entity
        your_turn_calls = [c for c in sound.play_shared.call_args_list
                           if c == call("your_turn", SoundCategory.ALERT)]
        assert len(your_turn_calls) == 0

    def test_damage_taken_local(self, bridge, sound):
        EventBus.emit(ENTITY_DAMAGED, {"target": "Hero", "damage": 5})
        sound.play.assert_called_with("damage_taken", SoundCategory.ALERT)

    def test_damage_dealt_non_local(self, bridge, sound):
        EventBus.emit(ENTITY_DAMAGED, {"target": "Goblin", "damage": 5})
        sound.play.assert_called_with("damage_dealt", SoundCategory.COMBAT)


class TestDMHearsAll:

    def test_dm_hears_all_turns(self, sound):
        bridge = SoundEventBridge(sound, viewer_entity_name="")
        bridge.start()
        EventBus.emit(TURN_STARTED, {"entity": "Goblin", "round": 1})
        sound.play_shared.assert_any_call("your_turn", SoundCategory.ALERT)
        bridge.stop()


class TestLifecycle:

    def test_stop_unsubscribes(self, sound):
        bridge = SoundEventBridge(sound, viewer_entity_name="Hero")
        bridge.start()
        bridge.stop()
        sound.reset_mock()
        EventBus.emit(COMBAT_STARTED, {})
        sound.play_shared.assert_not_called()

    def test_set_viewer(self, sound):
        bridge = SoundEventBridge(sound, viewer_entity_name="Hero")
        bridge.set_viewer("Mage")
        assert bridge._viewer == "Mage"

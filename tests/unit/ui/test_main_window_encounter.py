"""MainWindow encounter integration: menu actions, initiative panel, thread safety."""

import threading

import pytest

from core.engine.encounter import TurnInfo
from models.entities.game_entity import GameEntity
from ui.main_window import MainWindow


@pytest.fixture(autouse=True)
def stub_event_bus(monkeypatch):
    monkeypatch.setattr(
        "core.gameCreation.event_bus.EventBus.emit",
        classmethod(lambda cls, *a, **k: None),
    )


@pytest.fixture
def settings():
    class S:
        config_version = 1

        def __getitem__(self, key):
            return None

        def get(self, key, default=None):
            return default

    return S()


@pytest.fixture
def mw(qapp, settings):
    return MainWindow(settings, grid_type="square", rows=2, cols=3)


def _place(mw, *entities):
    tiles = [i for i in mw.scene.items() if hasattr(i, "tile_data")]
    for tile, ent in zip(tiles, entities):
        tile.tile_data.entities.append(ent)


def _two_entities(mw):
    _place(mw, GameEntity("Hero", "player"), GameEntity("Goblin", "enemy"))


def _rows(mw):
    return mw.initiative_panel._list.count()


def test_start_without_entities_shows_status(mw):
    mw.start_encounter()
    assert not mw.gamemaster.encounter.is_active
    assert "no entities" in mw.statusBar().currentMessage()
    assert mw._start_encounter_action.isEnabled()
    assert not mw._next_turn_action.isEnabled()
    assert not mw.initiative_panel.next_turn_button.isEnabled()


def test_start_populates_panel_and_highlights_current(mw):
    _two_entities(mw)
    mw.start_encounter()
    enc = mw.gamemaster.encounter
    assert enc.is_active
    assert _rows(mw) == 2
    assert mw.initiative_panel._current_entity == enc.current_entity_name
    assert mw.initiative_panel._round_label.text() == "Round: 1"
    assert not mw._initiative_dock.isHidden()
    assert not mw._start_encounter_action.isEnabled()
    assert mw._next_turn_action.isEnabled() and mw._end_encounter_action.isEnabled()
    assert mw.initiative_panel.next_turn_button.isEnabled()


def test_next_turn_button_advances(mw):
    _two_entities(mw)
    mw.start_encounter()
    first = mw.gamemaster.encounter.current_entity_name
    mw.initiative_panel.next_turn_button.click()
    second = mw.gamemaster.encounter.current_entity_name
    assert second != first
    assert mw.initiative_panel._current_entity == second
    mw.next_turn()
    assert mw.gamemaster.encounter.round_number == 2
    assert mw.initiative_panel._round_label.text() == "Round: 2"


def test_end_clears_panel_and_disables_next(mw):
    _two_entities(mw)
    mw.start_encounter()
    mw.end_encounter()
    assert not mw.gamemaster.encounter.is_active
    assert _rows(mw) == 0
    assert mw.initiative_panel._round_label.text() == "Round: --"
    assert not mw.initiative_panel.next_turn_button.isEnabled()
    assert not mw._next_turn_action.isEnabled()
    assert mw._start_encounter_action.isEnabled()


def test_gamemaster_kept_while_active_and_listener_not_duplicated(mw):
    _two_entities(mw)
    mw.start_encounter()
    gm = mw.gamemaster
    assert mw.get_gamemaster() is gm
    mw.end_encounter()
    gm2 = mw.get_gamemaster()
    assert gm2 is not gm
    assert mw._encounter_listener not in gm.encounter._listeners
    assert gm2.encounter._listeners.count(mw._encounter_listener) == 1


def test_listener_from_background_thread_updates_panel(mw, qtbot):
    _two_entities(mw)
    mw.start_encounter()
    name = mw.gamemaster.encounter.current_entity_name
    other = "Goblin" if name == "Hero" else "Hero"
    t = threading.Thread(target=mw._encounter_listener, args=(TurnInfo(other, 3),))
    t.start()
    t.join()
    qtbot.waitUntil(lambda: mw.initiative_panel._current_entity == other, timeout=2000)
    assert mw.initiative_panel._round_label.text() == "Round: 3"

    t = threading.Thread(target=mw._encounter_listener, args=(TurnInfo(None, 3),))
    t.start()
    t.join()
    qtbot.waitUntil(lambda: _rows(mw) == 0, timeout=2000)


def test_remote_turn_change_shows_dock_and_highlight(mw):
    mw._on_remote_turn_changed("Goblin", 4)
    assert not mw._initiative_dock.isHidden()
    assert mw.initiative_panel._current_entity == "Goblin"
    assert mw.initiative_panel._round_label.text() == "Round: 4"

"""MainWindow auto-play of AI-controlled enemy turns."""

import pytest

from models.entities.game_entity import GameEntity
from ui import main_window as mw_module
from ui.main_window import MainWindow


@pytest.fixture(autouse=True)
def stub_event_bus(monkeypatch):
    monkeypatch.setattr(
        "core.gameCreation.event_bus.EventBus.emit",
        classmethod(lambda cls, *a, **k: None),
    )
    monkeypatch.setattr(mw_module, "AI_TURN_DELAY_MS", 0)


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


class _FixedRng:
    """Deterministic initiative: earlier names in ``order`` act first."""

    def __init__(self, order, names_in_roll_order):
        self._values = []
        for name in names_in_roll_order:
            self._values += [100 - order.index(name), 1]  # roll, tiebreaker

    def randint(self, a, b):
        return self._values.pop(0)


def _setup(mw, monkeypatch, entities, order):
    tiles = [i for i in mw.scene.items() if hasattr(i, "tile_data")]
    for tile, ent in zip(tiles, entities):
        tile.tile_data.entities.append(ent)
    orig = mw.get_gamemaster

    def patched():
        gm = orig()
        if not gm.encounter.is_active:
            gm.encounter._tracker._rng = _FixedRng(order, [e.name for e in gm.game_entities])
        return gm

    monkeypatch.setattr(mw, "get_gamemaster", patched)


def _spy(mw, monkeypatch):
    calls = []
    orig = mw.get_gamemaster

    def patched():
        gm = orig()
        enc = gm.encounter
        if not getattr(enc, "_spied", False):
            real = enc.take_ai_turn

            def wrapped(adapter):
                calls.append(enc.current_entity_name)
                return real(adapter)

            enc.take_ai_turn = wrapped
            enc._spied = True
        return gm

    monkeypatch.setattr(mw, "get_gamemaster", patched)
    return calls


def _current(mw):
    return mw.gamemaster.encounter.current_entity_name


def test_enemy_turn_played_then_player(mw, qtbot, monkeypatch):
    _setup(mw, monkeypatch, [GameEntity("Hero", "player"), GameEntity("Goblin", "enemy")],
           ["Goblin", "Hero"])
    calls = _spy(mw, monkeypatch)
    mw.start_encounter()
    qtbot.waitUntil(lambda: _current(mw) == "Hero", timeout=3000)
    assert calls == ["Goblin"]
    assert mw.statusBar().currentMessage().startswith("Goblin:")


def test_autoplay_unchecked_does_nothing(mw, qtbot, monkeypatch):
    _setup(mw, monkeypatch, [GameEntity("Hero", "player"), GameEntity("Goblin", "enemy")],
           ["Goblin", "Hero"])
    calls = _spy(mw, monkeypatch)
    mw._autoplay_action.setChecked(False)
    mw.start_encounter()
    qtbot.wait(100)
    assert _current(mw) == "Goblin"
    assert calls == []


def test_autoplay_checked_by_default(mw):
    assert mw._autoplay_action.isCheckable() and mw._autoplay_action.isChecked()


def test_claimed_enemy_not_auto_played(mw, qtbot, monkeypatch):
    _setup(mw, monkeypatch, [GameEntity("Hero", "player"), GameEntity("Goblin", "enemy")],
           ["Goblin", "Hero"])
    calls = _spy(mw, monkeypatch)

    class SM:
        is_hosting = True

        def claimed_entities(self):
            return {"Goblin"}

    mw.session_manager = SM()
    mw.start_encounter()
    qtbot.wait(100)
    assert _current(mw) == "Goblin"
    assert calls == []


def test_stale_callback_after_end_is_ignored(mw, qtbot, monkeypatch):
    _setup(mw, monkeypatch, [GameEntity("Hero", "player"), GameEntity("Goblin", "enemy")],
           ["Goblin", "Hero"])
    calls = _spy(mw, monkeypatch)
    mw.start_encounter()
    mw.end_encounter()  # timer is still pending
    qtbot.wait(100)
    assert calls == []
    assert not mw.gamemaster.encounter.is_active
    assert mw.statusBar().currentMessage() == "Encounter ended"


def test_stale_callback_after_manual_next_turn_is_ignored(mw, qtbot, monkeypatch):
    _setup(mw, monkeypatch, [GameEntity("Hero", "player"), GameEntity("Goblin", "enemy")],
           ["Goblin", "Hero"])
    calls = _spy(mw, monkeypatch)
    mw.start_encounter()
    mw.next_turn()  # user skips before the timer fires
    qtbot.wait(100)
    assert calls == []
    assert _current(mw) == "Hero"


def test_two_consecutive_enemies_both_act(mw, qtbot, monkeypatch):
    _setup(mw, monkeypatch,
           [GameEntity("Hero", "player"), GameEntity("Goblin", "enemy"), GameEntity("Orc", "enemy")],
           ["Goblin", "Orc", "Hero"])
    calls = _spy(mw, monkeypatch)
    mw.start_encounter()
    qtbot.waitUntil(lambda: _current(mw) == "Hero", timeout=3000)
    assert calls == ["Goblin", "Orc"]
    assert mw.gamemaster.encounter.round_number == 1


def test_no_living_players_skips_autoplay(mw, qtbot, monkeypatch):
    hero = GameEntity("Hero", "player")
    hero.hp = 0
    _setup(mw, monkeypatch, [hero, GameEntity("Goblin", "enemy")], ["Goblin", "Hero"])
    calls = _spy(mw, monkeypatch)
    mw.start_encounter()
    qtbot.wait(100)
    assert calls == []
    assert _current(mw) == "Goblin"
    assert mw.statusBar().currentMessage() == "Encounter over: no players left"

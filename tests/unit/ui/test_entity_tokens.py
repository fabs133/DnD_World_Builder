"""Entity token layer: drawing, colours, movement, scene teardown."""

import pytest

from models.entities.game_entity import GameEntity
from ui.entity_tokens import (
    DEAD_COLOR,
    TOKEN_COLORS,
    EntityTokenLayer,
    entity_kind,
    token_color,
    token_slots,
    token_tooltip,
)
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


def _tiles(mw):
    return sorted(
        (i for i in mw.scene.items() if hasattr(i, "tile_data")),
        key=lambda t: t.tile_data.position,
    )


def test_pure_helpers():
    assert entity_kind(GameEntity("A", "Enemy")) == "enemy"
    assert entity_kind(GameEntity("A", "dragon")) == "other"
    assert len(token_slots(1, 50)) == 1
    assert len(token_slots(9, 50)) == 4
    assert token_slots(0, 50) == []
    assert "Bob (npc) HP 10/10" == token_tooltip(GameEntity("Bob", "npc"))


def test_tokens_drawn_per_entity(mw):
    t = _tiles(mw)
    t[0].tile_data.entities.append(GameEntity("Hero", "player"))
    t[1].tile_data.entities.extend([GameEntity("A", "enemy"), GameEntity("B", "enemy")])
    mw.entity_tokens.refresh()
    assert len(mw.entity_tokens.tokens) == 3
    mw.entity_tokens.refresh()
    assert len(mw.entity_tokens.tokens) == 3


def test_color_differs_by_type():
    colors = {token_color(GameEntity("x", k)) for k in ("player", "enemy", "npc", "other")}
    assert len(colors) == 4
    assert token_color(GameEntity("x", "player")) == TOKEN_COLORS["player"]


def test_dead_entity_greyed(mw):
    e = GameEntity("Gob", "enemy")
    e.hp = 0
    _tiles(mw)[0].tile_data.entities.append(e)
    mw.entity_tokens.refresh()
    (token,) = mw.entity_tokens.tokens
    assert token.brush().color().name().upper() == DEAD_COLOR.upper()


def test_refresh_moves_token(mw):
    t = _tiles(mw)
    e = GameEntity("Hero", "player")
    t[0].tile_data.entities.append(e)
    mw.entity_tokens.refresh()
    (token,) = mw.entity_tokens.tokens
    assert token.scenePos() == t[0].sceneBoundingRect().center()
    t[0].tile_data.entities.remove(e)
    t[4].tile_data.entities.append(e)
    mw.entity_tokens.refresh()
    (token,) = mw.entity_tokens.tokens
    assert token.scenePos() == t[4].sceneBoundingRect().center()


def test_tokens_do_not_accept_mouse(mw):
    _tiles(mw)[0].tile_data.entities.append(GameEntity("Hero", "player"))
    mw.entity_tokens.refresh()
    assert int(mw.entity_tokens.tokens[0].acceptedMouseButtons()) == 0


def test_scene_clear_then_refresh_is_safe(mw):
    _tiles(mw)[0].tile_data.entities.append(GameEntity("Hero", "player"))
    mw.entity_tokens.refresh()
    mw.scene.clear()
    mw.entity_tokens.refresh()
    assert mw.entity_tokens.tokens == []
    layer = EntityTokenLayer(mw.scene)
    layer.refresh()


def test_entity_event_callback_refreshes(mw):
    _tiles(mw)[0].tile_data.entities.append(GameEntity("Hero", "player"))
    mw._on_entities_changed({"entity_name": "Hero"})
    assert len(mw.entity_tokens.tokens) == 1

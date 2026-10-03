"""Fog-of-war player view: overlay items, token hiding, explored memory."""

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPolygonF

from core.engine.vision import Visibility
from models.entities.game_entity import GameEntity
from models.tiles.tile_data import TileTag
from ui.fog_overlay import FOG_Z, FogOfWarLayer
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


def _make(qapp, settings, grid="square", rows=1, cols=30):
    return MainWindow(settings, grid_type=grid, rows=rows, cols=cols)


@pytest.fixture
def mw(qapp, settings):
    return _make(qapp, settings)


def _tile(mw, pos):
    return next(
        i for i in mw.scene.items() if hasattr(i, "tile_data") and i.tile_data.position == pos
    )


def _hero(range_tiles=3):
    hero = GameEntity("Hero", "player")
    hero.vision_range = range_tiles
    return hero


def _covered(mw):
    """Map position -> overlay item, matched by overlay centre inside the tile."""
    out = {}
    for ov in mw.fog_overlay.overlays:
        c = ov.polygon().boundingRect().center()
        for t in (i for i in mw.scene.items() if hasattr(i, "tile_data")):
            if t.sceneBoundingRect().contains(c):
                out[t.tile_data.position] = ov
    return out


def test_dm_view_has_no_overlay(mw):
    _tile(mw, (0, 0)).tile_data.entities.append(_hero())
    mw.refresh_entity_tokens()
    assert mw.fog_overlay.overlays == []
    assert not mw._player_view_action.isChecked()
    assert not mw._reset_fog_action.isEnabled()


def test_player_view_hides_far_tiles(mw):
    _tile(mw, (0, 0)).tile_data.entities.append(_hero(3))
    mw.refresh_entity_tokens()
    mw._player_view_action.setChecked(True)
    covered = _covered(mw)
    assert (0, 3) not in covered and (0, 0) not in covered
    assert (0, 4) in covered and (0, 29) in covered
    assert len(mw.fog_overlay.overlays) == 30 - 4
    ov = covered[(0, 10)]
    assert ov.zValue() == FOG_Z
    assert ov.acceptedMouseButtons() == Qt.NoButton
    assert ov.brush().color().alpha() == 255
    mw._player_view_action.setChecked(False)
    assert mw.fog_overlay.overlays == []


def test_blocks_vision_hides_tile_behind(mw):
    _tile(mw, (0, 0)).tile_data.entities.append(_hero(10))
    _tile(mw, (0, 2)).tile_data.tags.append(TileTag.BLOCKS_VISION)
    mw._player_view_action.setChecked(True)
    mw.refresh_entity_tokens()
    covered = _covered(mw)
    assert (0, 2) not in covered  # the wall itself is visible
    assert (0, 3) in covered


def test_moving_player_leaves_explored(mw):
    a, b = _tile(mw, (0, 0)).tile_data, _tile(mw, (0, 20)).tile_data
    hero = _hero(3)
    a.entities.append(hero)
    mw._player_view_action.setChecked(True)
    mw.refresh_entity_tokens()
    a.entities.remove(hero)
    b.entities.append(hero)
    mw.refresh_entity_tokens()
    assert mw.fog_overlay.fog.state((0, 0)) is Visibility.EXPLORED
    assert mw.fog_overlay.fog.state((0, 10)) is Visibility.HIDDEN
    covered = _covered(mw)
    assert covered[(0, 0)].brush().color().alpha() < 255
    assert covered[(0, 10)].brush().color().alpha() == 255
    # off then on keeps memory; reset clears it
    mw._player_view_action.setChecked(False)
    mw._player_view_action.setChecked(True)
    assert mw.fog_overlay.fog.state((0, 0)) is Visibility.EXPLORED
    mw._reset_fog_action.trigger()
    assert mw.fog_overlay.fog.state((0, 0)) is Visibility.HIDDEN


def test_enemy_token_hidden_in_player_view(mw):
    _tile(mw, (0, 0)).tile_data.entities.append(_hero(3))
    _tile(mw, (0, 1)).tile_data.entities.append(GameEntity("Gob", "enemy"))
    _tile(mw, (0, 20)).tile_data.entities.append(GameEntity("Orc", "enemy"))
    mw.refresh_entity_tokens()
    assert len(mw.entity_tokens.tokens) == 3
    mw._player_view_action.setChecked(True)
    shown = [t.toolTip().split()[0] for t in mw.entity_tokens.tokens if t.isVisible()]
    assert sorted(shown) == ["Gob", "Hero"]
    mw.refresh_entity_tokens()  # tokens are rebuilt; hiding is reapplied
    shown = [t.toolTip().split()[0] for t in mw.entity_tokens.tokens if t.isVisible()]
    assert sorted(shown) == ["Gob", "Hero"]
    mw._player_view_action.setChecked(False)
    assert len(mw.entity_tokens.tokens) == 3
    assert all(t.isVisible() for t in mw.entity_tokens.tokens)


def test_no_players_hint_and_all_hidden(mw):
    mw._player_view_action.setChecked(True)
    assert "no player entities" in mw.statusBar().currentMessage()
    assert len(mw.fog_overlay.overlays) == 30


def test_hex_overlay_is_hexagon(qapp, settings):
    mw = _make(qapp, settings, grid="hex", rows=3, cols=3)
    mw._player_view_action.setChecked(True)
    overlays = mw.fog_overlay.overlays
    assert len(overlays) == 9
    for ov in overlays:
        assert ov.polygon().count() in (6, 7)  # closed or open hexagon
    tile = _tile(mw, (0, 0))
    assert ov.polygon().boundingRect().width() <= tile.sceneBoundingRect().width() + 1


def test_scene_rebuild_does_not_crash(mw):
    _tile(mw, (0, 0)).tile_data.entities.append(_hero())
    mw._player_view_action.setChecked(True)
    mw.refresh_entity_tokens()
    assert mw.fog_overlay.fog.state((0, 0)) is Visibility.VISIBLE
    mw.scene.clear()
    mw.init_grid(1, 5)
    assert mw.fog_overlay.fog.state((0, 0)) is Visibility.HIDDEN
    assert len(mw.fog_overlay.overlays) == 5
    mw.scene.clear()
    mw.fog_overlay.refresh()
    assert mw.fog_overlay.overlays == []


def test_tile_modified_refreshes(mw):
    _tile(mw, (0, 0)).tile_data.entities.append(_hero(10))
    mw._player_view_action.setChecked(True)
    mw.refresh_entity_tokens()
    assert (0, 5) not in _covered(mw)
    _tile(mw, (0, 2)).tile_data.tags.append(TileTag.BLOCKS_VISION)
    mw._on_tile_modified()
    assert (0, 5) in _covered(mw)


def test_layer_standalone_empty_scene(qapp):
    from PyQt5.QtWidgets import QGraphicsScene

    layer = FogOfWarLayer(QGraphicsScene())
    layer.set_enabled(True)
    layer.update([])
    assert layer.overlays == [] and not isinstance(QPolygonF(), type(None))

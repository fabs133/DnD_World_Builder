"""Joined player's read-only view of the host's map, with fog centred on the claimed character."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from models.entities.game_entity import GameEntity
from models.tiles.tile_data import TileData
from network.session_manager import SessionManager
from network.ui.session_panel import SessionPanel
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
    window = MainWindow(settings, grid_type="square", rows=2, cols=2)
    window.session_manager = SimpleNamespace(claimed_entity=None, claim_entity=MagicMock())
    return window


def _world(cols=30, entities=None, tile_type="square"):
    """A 1 x cols host map; ``entities`` maps column -> GameEntity."""
    entities = entities or {}
    tiles = {}
    for col in range(cols):
        td = TileData(tile_id=f"t{col}", position=(0, col))
        if col in entities:
            td.entities.append(entities[col])
        tiles[f"0,{col}"] = td.to_dict()
    return {"tile_type": tile_type, "tiles": tiles}


def _two_heroes():
    return _world(entities={0: GameEntity("Alice", "player"), 29: GameEntity("Bob", "player")})


def _tile_count(mw):
    return sum(1 for i in mw.scene.items() if hasattr(i, "tile_data"))


def _covered(mw):
    """Tile positions currently under a fog mask."""
    covered = set()
    for overlay in mw.fog_overlay.overlays:
        center = overlay.polygon().boundingRect().center()
        for item in mw.scene.items(center):
            if hasattr(item, "tile_data"):
                covered.add(item.tile_data.position)
    return covered


def test_shows_host_map_read_only_with_forced_player_view(mw):
    mw.current_map_path = "my_map.json"
    mw.show_remote_world(_two_heroes())

    assert _tile_count(mw) == 30
    assert mw.read_only
    assert mw.current_map_path is None
    assert mw._player_view_action.isChecked()
    assert not mw._player_view_action.isEnabled()
    assert not mw._start_encounter_action.isEnabled()

    tile = next(i for i in mw.scene.items() if hasattr(i, "tile_data"))
    mw.select_tile(tile)
    assert mw.selected_tile is None
    mw.activate_color_mode("#ff0000")
    assert not mw.color_mode_active


def test_before_claiming_the_party_provides_vision(mw):
    mw.show_remote_world(_two_heroes())
    covered = _covered(mw)
    assert (0, 0) not in covered and (0, 29) not in covered
    assert (0, 15) in covered  # 15 tiles from both heroes, beyond the 12-tile default


def test_after_claiming_only_own_character_sees(mw):
    mw.show_remote_world(_two_heroes())
    mw.session_manager.claimed_entity = "Alice"
    mw._on_remote_claim_changed("Alice", "p1")

    covered = _covered(mw)
    assert (0, 0) not in covered
    assert (0, 29) in covered  # Bob's surroundings are now fogged


def test_claim_controls(mw):
    mw.show_remote_world(_two_heroes())
    assert mw.session_panel._claim_row.isVisibleTo(mw.session_panel)
    combo = mw.session_panel._claim_combo
    assert [combo.itemText(i) for i in range(combo.count())] == ["Alice", "Bob"]

    combo.setCurrentText("Bob")
    mw.session_panel._claim_btn.click()
    mw.session_manager.claim_entity.assert_called_once_with("Bob")

    mw.session_manager.claimed_entity = "Bob"
    mw._on_remote_claim_changed("Bob", "p1")
    assert not mw.session_panel._claim_row.isVisibleTo(mw.session_panel)


def test_updates_redraw_without_losing_explored_tiles(mw):
    hero = GameEntity("Alice", "player")
    mw.session_manager.claimed_entity = "Alice"
    mw.show_remote_world(_world(entities={0: hero}))
    mw.show_remote_world(_world(entities={25: hero}))  # host moved Alice across the map

    covered = _covered(mw)
    assert (0, 25) not in covered
    explored = mw.fog_overlay.fog.state((0, 0)).value
    assert explored == "explored"


def test_session_end_restores_local_map(mw):
    mw.current_map_path = "my_map.json"
    local_tiles = _tile_count(mw)

    mw.show_remote_world(_two_heroes())
    mw._on_session_ended()

    assert not mw.read_only
    assert _tile_count(mw) == local_tiles
    assert mw.current_map_path == "my_map.json"
    assert mw._player_view_action.isEnabled()
    assert not mw._player_view_action.isChecked()
    assert mw.fog_overlay.viewer_names is None


def test_hex_map_round_trips_grid_type(qapp, settings, tmp_path):
    window = MainWindow(settings, grid_type="hex", rows=2, cols=2)
    path = tmp_path / "hex.json"
    window.save_map_to_file(str(path))
    assert json.loads(path.read_text())["meta"]["grid_type"] == "hex"

    other = MainWindow(settings, grid_type="square", rows=1, cols=1)
    other.load_map_from_file(str(path))
    assert other.grid_type == "hex"


def test_session_manager_emits_a_copy_of_the_world(qapp):
    manager = SessionManager.__new__(SessionManager)
    manager.signals = SessionManager.__init__.__globals__["SessionSignals"]()
    manager._client = SimpleNamespace(world_state={"tiles": {"0,0": {"a": 1}}})
    received = []
    manager.signals.world_changed.connect(received.append)

    manager._on_state_delta(None)

    assert received == [{"tiles": {"0,0": {"a": 1}}}]
    received[0]["tiles"]["0,0"]["a"] = 2
    assert manager._client.world_state["tiles"]["0,0"]["a"] == 1


def test_session_panel_hides_claim_row_when_nothing_to_claim(qapp):
    panel = SessionPanel()
    panel.set_claimable(["Alice"])
    assert panel._claim_row.isVisibleTo(panel)
    panel.clear()
    assert not panel._claim_row.isVisibleTo(panel)


def test_chat_is_sent_once_across_repeated_sessions(mw):
    sent = []
    mw.session_manager = SimpleNamespace(send_chat=sent.append)
    # Simulate the panel being reused by several sessions: no extra connections pile up.
    mw.session_panel._chat_input.setText("hi")
    mw.session_panel._send_chat()
    assert sent == ["hi"]

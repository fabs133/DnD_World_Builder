"""Tests for EntitiesPanel: list population, add, delete, duplicate."""

import copy
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from models.entities.game_entity import GameEntity
from models.tiles.tile_data import TileData
from ui.panels.entities_panel import EntitiesPanel


@pytest.fixture(autouse=True)
def stub_event_bus(monkeypatch):
    """Prevent EventBus side-effects."""
    monkeypatch.setattr(
        "core.gameCreation.event_bus.EventBus.emit",
        classmethod(lambda cls, *a, **k: None),
    )


@pytest.fixture
def tile_data():
    td = TileData(tile_id="t1", position=(1, 2))
    td.entities = [
        GameEntity(name="Goblin", entity_type="enemy"),
        GameEntity(name="Paladin", entity_type="player"),
    ]
    return td


@pytest.fixture
def panel(qapp, tile_data):
    mw = MagicMock()
    sp = MagicMock()
    p = EntitiesPanel(mw)
    p.load(tile_data, mw, sp)
    return p


class TestEntitiesPanelList:

    def test_list_populated(self, panel, tile_data):
        assert panel._list.count() == len(tile_data.entities)

    def test_list_empty_when_no_entities(self, qapp):
        mw = MagicMock()
        p = EntitiesPanel(mw)
        td = TileData(tile_id="t2", position=(0, 0))
        p.load(td, mw, MagicMock())
        assert p._list.count() == 0


class TestDuplicate:

    def test_duplicate_creates_copy(self, panel, tile_data):
        original = tile_data.entities[0]
        panel._duplicate_entity(original)
        assert len(tile_data.entities) == 3
        assert tile_data.entities[-1].name == "Goblin (copy)"
        assert tile_data.entities[-1] is not original


class TestDelete:

    def test_delete_removes_entity(self, panel, tile_data, monkeypatch):
        # Stub the QMessageBox guard
        monkeypatch.setattr(
            "ui.panels.entities_panel.QMessageBox.question",
            lambda *a, **k: None,
        )
        entity = tile_data.entities[0]
        panel._delete_entity(entity)
        assert entity not in tile_data.entities
        assert panel._list.count() == 1

    def test_delete_nonexistent_entity_is_safe(self, panel, tile_data, monkeypatch):
        monkeypatch.setattr(
            "ui.panels.entities_panel.QMessageBox.question",
            lambda *a, **k: None,
        )
        fake_entity = GameEntity(name="Ghost", entity_type="enemy")
        panel._delete_entity(fake_entity)
        # Should not crash, entity count unchanged
        assert len(tile_data.entities) == 2


class TestGuardUnsaved:

    def test_guard_returns_true_when_no_editor(self, panel):
        panel._editor.setVisible(False)
        assert panel._guard_unsaved() is True

    def test_guard_returns_true_when_not_dirty(self, panel, tile_data):
        panel._editor.load(
            tile_data.entities[0], 0, tile_data, MagicMock()
        )
        panel._editor._dirty = False
        assert panel._guard_unsaved() is True

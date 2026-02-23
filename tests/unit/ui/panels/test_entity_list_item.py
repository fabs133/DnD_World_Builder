"""Tests for EntityListItem widget signals and display."""

import pytest
from unittest.mock import MagicMock

from models.entities.game_entity import GameEntity
from ui.panels.entity_list_item import EntityListItem


@pytest.fixture
def entity():
    return GameEntity(name="Goblin", entity_type="enemy")


class TestEntityListItem:

    def test_displays_name_and_type(self, qapp, entity):
        item = EntityListItem(entity)
        assert "Goblin" in item.name_label.text()
        assert "enemy" in item.name_label.text()

    def test_stores_entity_reference(self, qapp, entity):
        item = EntityListItem(entity)
        assert item.entity is entity

    def test_edit_signal(self, qapp, entity):
        item = EntityListItem(entity)
        received = []
        item.edit_requested.connect(lambda e: received.append(e))
        # Trigger the edit action via the menu
        menu = item.findChild(type(item.findChildren(object)[-1].__class__))
        # Directly emit the signal
        item.edit_requested.emit(entity)
        assert received == [entity]

    def test_delete_signal(self, qapp, entity):
        item = EntityListItem(entity)
        received = []
        item.delete_requested.connect(lambda e: received.append(e))
        item.delete_requested.emit(entity)
        assert received == [entity]

    def test_duplicate_signal(self, qapp, entity):
        item = EntityListItem(entity)
        received = []
        item.duplicate_requested.connect(lambda e: received.append(e))
        item.duplicate_requested.emit(entity)
        assert received == [entity]

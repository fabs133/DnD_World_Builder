"""Tests for zone entity lookup — load_zone data types, entity_clicked signals, _find_entity."""

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QListWidgetItem

from ui.exploration.zone_detail_widget import ZoneDetailWidget
from models.exploration.zone_scene_data import ZoneSceneData, SceneObject
from models.entities.game_entity import GameEntity


def make_entity(name, entity_type="player", hp=20, position=(0, 0),
                armor_class=12, speed=30):
    e = GameEntity(name=name, entity_type=entity_type,
                   stats={"hp": hp, "max_hp": hp, "armor_class": armor_class,
                          "speed": speed})
    e.position = position
    e.movement_remaining = speed
    e.action_used = False
    e.bonus_action_used = False
    e.reaction_used = False
    return e


def _make_zone_scene_data(objects=None):
    """Create a minimal ZoneSceneData."""
    objs = objects or []
    objects_by_depth = {1: [], 2: [], 3: objs}
    return ZoneSceneData(
        zone_id="test_zone",
        zone_label="Test Zone",
        zone_description="A test zone",
        objects_by_depth=objects_by_depth,
        nav_arrows=[],
    )


def _make_scene_object(name, obj_type="npc", faction="friendly"):
    return SceneObject(
        name=name, obj_type=obj_type, depth=3,
        x_percent=0.5, faction=faction,
    )


# ── load_zone data types ────────────────────────────────────────────


class TestLoadZoneDataTypes:

    def test_stores_game_entity_in_userole(self, qapp):
        widget = ZoneDetailWidget()
        entity = make_entity("Captain", "npc", hp=30, position=(2, 3))
        scene_obj = _make_scene_object("Captain")
        scene_data = _make_zone_scene_data([scene_obj])

        widget.load_zone(scene_data, entities=[entity])

        item = widget._entity_list.item(0)
        data = item.data(Qt.UserRole)
        assert data is entity  # Should be the GameEntity object

    def test_fallback_stores_string_when_no_entity(self, qapp):
        widget = ZoneDetailWidget()
        scene_obj = _make_scene_object("Unknown NPC")
        scene_data = _make_zone_scene_data([scene_obj])

        widget.load_zone(scene_data, entities=[])  # No entities provided

        item = widget._entity_list.item(0)
        data = item.data(Qt.UserRole)
        assert isinstance(data, str)
        assert data == "Unknown NPC"

    def test_entity_map_matches_scene_objects(self, qapp):
        widget = ZoneDetailWidget()
        captain = make_entity("Captain", "npc", hp=30)
        guard = make_entity("Guard", "npc", hp=20)
        scene_objs = [_make_scene_object("Captain"), _make_scene_object("Guard")]
        scene_data = _make_zone_scene_data(scene_objs)

        widget.load_zone(scene_data, entities=[captain, guard])

        for i in range(widget._entity_list.count()):
            item = widget._entity_list.item(i)
            data = item.data(Qt.UserRole)
            assert not isinstance(data, str), f"Item {i} stored string instead of entity"

    def test_load_zone_hides_npc_panel(self, qapp):
        widget = ZoneDetailWidget()
        scene_data = _make_zone_scene_data([])
        widget.load_zone(scene_data)
        assert not widget._npc_panel.isVisible()

    def test_load_zone_name_stored_as_fallback(self, qapp):
        widget = ZoneDetailWidget()
        entity = make_entity("Captain", "npc")
        scene_obj = _make_scene_object("Captain")
        scene_data = _make_zone_scene_data([scene_obj])

        widget.load_zone(scene_data, entities=[entity])

        item = widget._entity_list.item(0)
        name_fallback = item.data(Qt.UserRole + 1)
        assert name_fallback == "Captain"


# ── load_simple_tile data types ─────────────────────────────────────


class TestLoadSimpleTileDataTypes:

    def test_stores_entity_objects(self, qapp):
        widget = ZoneDetailWidget()
        entities = [
            make_entity("Captain", "npc"),
            make_entity("Guard", "npc"),
        ]
        widget.load_simple_tile("Town Square", "A quiet place", entities)

        for i in range(widget._entity_list.count()):
            item = widget._entity_list.item(i)
            data = item.data(Qt.UserRole)
            assert hasattr(data, "name"), f"Item {i} is not an entity object"

    def test_empty_entities_shows_placeholder(self, qapp):
        widget = ZoneDetailWidget()
        widget.load_simple_tile("Empty Room", "", [])
        assert widget._entity_list.count() == 1
        item = widget._entity_list.item(0)
        assert "no one here" in item.text().lower()


# ── _on_list_entity_clicked signal types ────────────────────────────


class TestEntityClickedSignalTypes:

    def test_list_click_emits_entity_object(self, qapp):
        widget = ZoneDetailWidget()
        entity = make_entity("Captain", "npc")
        widget.load_simple_tile("Zone", "", [entity])

        received = []
        widget.entity_clicked.connect(lambda e: received.append(e))

        # Simulate a real click through the sidebar's item handler
        item = widget._entity_list.item(0)
        widget._entity_sidebar._on_item_clicked(item)

        assert len(received) == 1
        assert received[0] is entity

    def test_list_click_emits_string_for_fallback(self, qapp):
        widget = ZoneDetailWidget()
        scene_obj = _make_scene_object("Mystery NPC")
        scene_data = _make_zone_scene_data([scene_obj])
        widget.load_zone(scene_data, entities=[])  # No entity objects

        received = []
        widget.entity_clicked.connect(lambda e: received.append(e))

        item = widget._entity_list.item(0)
        widget._entity_sidebar._on_item_clicked(item)

        assert len(received) == 1
        assert isinstance(received[0], str)
        assert received[0] == "Mystery NPC"

    def test_entity_info_requested_emitted(self, qapp):
        widget = ZoneDetailWidget()
        entity = make_entity("Captain", "npc")
        widget.load_simple_tile("Zone", "", [entity])

        received = []
        widget.entity_info_requested.connect(lambda n, t: received.append((n, t)))

        item = widget._entity_list.item(0)
        widget._entity_sidebar._on_item_clicked(item)

        assert len(received) == 1
        assert received[0][0] == "Captain"


# ── NPC panel lifecycle ─────────────────────────────────────────────


class TestNpcPanelLifecycle:

    def test_show_npc_panel(self, qapp):
        widget = ZoneDetailWidget()
        widget.show_npc_panel("Captain", [{"id": "talk", "label": "Talk"}])
        # isVisible() requires a shown parent; use isHidden() for headless tests
        assert not widget._npc_panel.isHidden()

    def test_hide_npc_panel(self, qapp):
        widget = ZoneDetailWidget()
        widget.show_npc_panel("Captain", [{"id": "talk", "label": "Talk"}])
        widget.hide_npc_panel()
        assert not widget._npc_panel.isVisible()

    def test_load_zone_resets_npc_panel(self, qapp):
        widget = ZoneDetailWidget()
        widget.show_npc_panel("Captain", [{"id": "talk", "label": "Talk"}])
        scene_data = _make_zone_scene_data([])
        widget.load_zone(scene_data)
        assert not widget._npc_panel.isVisible()

    def test_load_simple_tile_resets_npc_panel(self, qapp):
        widget = ZoneDetailWidget()
        widget.show_npc_panel("Captain", [{"id": "talk", "label": "Talk"}])
        widget.load_simple_tile("Room", "", [])
        assert not widget._npc_panel.isVisible()

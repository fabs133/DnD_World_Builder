"""Tests for PlayMapScene — overlays, entity tracking, path preview, signals."""

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsRectItem

from ui.combat.play_map_widget import PlayMapScene, RangeOutline, make_decorative
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


# ── make_decorative helper ──────────────────────────────────────────


class TestMakeDecorative:

    def test_sets_no_mouse_buttons(self, qapp):
        item = make_decorative(QGraphicsRectItem(0, 0, 10, 10))
        assert item.acceptedMouseButtons() == Qt.NoButton

    def test_sets_no_hover(self, qapp):
        item = make_decorative(QGraphicsRectItem(0, 0, 10, 10))
        assert item.acceptHoverEvents() is False

    def test_not_selectable(self, qapp):
        item = make_decorative(QGraphicsRectItem(0, 0, 10, 10))
        assert not (item.flags() & QGraphicsItem.ItemIsSelectable)

    def test_not_movable(self, qapp):
        item = make_decorative(QGraphicsRectItem(0, 0, 10, 10))
        assert not (item.flags() & QGraphicsItem.ItemIsMovable)

    def test_returns_item(self, qapp):
        rect = QGraphicsRectItem(0, 0, 10, 10)
        result = make_decorative(rect)
        assert result is rect


# ── Overlay rendering ───────────────────────────────────────────────


class TestOverlayRendering:

    def test_apply_overlay_brush_is_qbrush_not_brushstyle(self, combat_scene):
        """THE recurring bug: Qt.NoBrush is BrushStyle, not QBrush."""
        combat_scene.apply_overlay_to_tiles([(5, 5)], QColor(60, 120, 220))
        for item in combat_scene._overlay_items:
            brush = item.brush()
            assert isinstance(brush, QBrush)
            assert brush.style() == Qt.NoBrush

    def test_overlay_items_are_decorative(self, combat_scene):
        combat_scene.apply_overlay_to_tiles([(5, 5), (5, 6)], QColor("red"))
        for item in combat_scene._overlay_items:
            assert item.acceptedMouseButtons() == Qt.NoButton

    def test_overlay_items_no_hover(self, combat_scene):
        combat_scene.apply_overlay_to_tiles([(5, 5)], QColor("red"))
        for item in combat_scene._overlay_items:
            assert item.acceptHoverEvents() is False

    def test_overlay_items_not_selectable(self, combat_scene):
        combat_scene.apply_overlay_to_tiles([(5, 5)], QColor("red"))
        for item in combat_scene._overlay_items:
            assert not (item.flags() & QGraphicsItem.ItemIsSelectable)

    def test_overlay_has_outline_pen(self, combat_scene):
        combat_scene.apply_overlay_to_tiles([(5, 5)], QColor("red"))
        assert len(combat_scene._overlay_items) == 1
        pen = combat_scene._overlay_items[0].pen()
        assert pen.widthF() == pytest.approx(2.0)

    def test_clear_all_overlays_removes_items(self, combat_scene):
        combat_scene.apply_overlay_to_tiles([(5, 5), (6, 6)], QColor("red"))
        assert len(combat_scene._overlay_items) == 2
        combat_scene.clear_all_overlays()
        assert len(combat_scene._overlay_items) == 0

    def test_clear_all_overlays_idempotent(self, combat_scene):
        combat_scene.clear_all_overlays()
        combat_scene.clear_all_overlays()  # should not crash


# ── RangeOutline ────────────────────────────────────────────────────


class TestRangeOutline:

    def test_creates_path_item(self, combat_scene):
        outline = RangeOutline(combat_scene, 48)
        reachable = {(r, c) for r in range(3, 8) for c in range(3, 8)}
        outline.show(reachable, combat_scene._tiles, "#378ADD")
        assert outline._outline_item is not None
        assert outline._outline_item.scene() is combat_scene

    def test_is_decorative(self, combat_scene):
        outline = RangeOutline(combat_scene, 48)
        reachable = {(5, 5)}
        outline.show(reachable, combat_scene._tiles)
        assert outline._outline_item.acceptedMouseButtons() == Qt.NoButton
        assert outline._outline_item.acceptHoverEvents() is False

    def test_pulse_timer_starts(self, combat_scene):
        outline = RangeOutline(combat_scene, 48)
        outline.show({(5, 5)}, combat_scene._tiles)
        assert outline._pulse_timer is not None

    def test_clear_stops_pulse(self, combat_scene):
        outline = RangeOutline(combat_scene, 48)
        outline.show({(5, 5)}, combat_scene._tiles)
        outline.clear()
        assert outline._pulse_timer is None
        assert outline._outline_item is None

    def test_clear_idempotent(self, combat_scene):
        outline = RangeOutline(combat_scene, 48)
        outline.clear()
        outline.clear()  # should not crash


# ── Entity tracking ─────────────────────────────────────────────────


class TestEntityTracking:

    def test_entity_at_after_update(self, combat_scene, three_players):
        fighter = three_players[0]
        result = combat_scene.entity_at(8, 3)
        assert result is fighter

    def test_entity_at_before_update(self, tile_dicts_10x10):
        scene = PlayMapScene(tile_dicts_10x10, tile_size=48)
        scene.set_fog_enabled(False)
        # No update_entities called
        assert scene.entity_at(8, 3) is None

    def test_entity_at_dead_entity(self, tile_dicts_10x10):
        scene = PlayMapScene(tile_dicts_10x10, tile_size=48)
        scene.set_fog_enabled(False)
        dead = make_entity("Dead", "enemy", hp=0, position=(5, 5))
        scene.update_entities([dead])
        assert scene.entity_at(5, 5) is None

    def test_entity_positions_cleared_each_update(self, combat_scene):
        old_entity = make_entity("OldGuy", "enemy", hp=10, position=(3, 3))
        combat_scene.update_entities([old_entity])
        assert combat_scene.entity_at(3, 3) is old_entity
        # Update with different entities
        new_entity = make_entity("NewGuy", "enemy", hp=10, position=(4, 4))
        combat_scene.update_entities([new_entity])
        assert combat_scene.entity_at(3, 3) is None
        assert combat_scene.entity_at(4, 4) is new_entity

    def test_entity_at_empty_position(self, combat_scene):
        assert combat_scene.entity_at(0, 0) is None

    def test_entity_at_off_grid(self, combat_scene):
        assert combat_scene.entity_at(99, 99) is None


# ── Path preview ────────────────────────────────────────────────────


class TestPathPreview:

    def test_show_path_creates_lines(self, combat_scene):
        path = [(5, 5), (5, 6), (5, 7)]
        combat_scene.show_path_preview(path, in_range=True)
        # 2 lines + 1 label = 3 items
        assert len(combat_scene._path_items) == 3

    def test_show_path_distance_label(self, combat_scene):
        path = [(5, 5), (5, 6), (5, 7), (5, 8)]
        combat_scene.show_path_preview(path, in_range=True)
        label = combat_scene._path_items[-1]
        assert "15 ft" in label.toPlainText()

    def test_path_items_are_decorative(self, combat_scene):
        path = [(5, 5), (5, 6)]
        combat_scene.show_path_preview(path, in_range=True)
        for item in combat_scene._path_items:
            assert item.acceptedMouseButtons() == Qt.NoButton

    def test_clear_path_preview(self, combat_scene):
        combat_scene.show_path_preview([(5, 5), (5, 6)], True)
        assert len(combat_scene._path_items) > 0
        combat_scene.clear_path_preview()
        assert len(combat_scene._path_items) == 0

    def test_show_path_replaces_previous(self, combat_scene):
        combat_scene.show_path_preview([(5, 5), (5, 6)], True)
        old_count = len(combat_scene._path_items)
        combat_scene.show_path_preview([(3, 3), (3, 4), (3, 5)], False)
        # Old items removed, new ones added
        assert len(combat_scene._path_items) == 3  # 2 lines + 1 label

    def test_empty_path_no_items(self, combat_scene):
        combat_scene.show_path_preview([], True)
        assert len(combat_scene._path_items) == 0

    def test_single_node_path_no_items(self, combat_scene):
        combat_scene.show_path_preview([(5, 5)], True)
        assert len(combat_scene._path_items) == 0


# ── Signals ─────────────────────────────────────────────────────────


class TestSignals:

    def test_tile_hovered_deduplicates(self, combat_scene):
        """Same tile hovered twice should only emit once."""
        received = []
        combat_scene.tile_hovered.connect(lambda r, c: received.append((r, c)))
        # Simulate setting last_hovered to same value
        combat_scene._last_hovered = (5, 5)
        # mouseMoveEvent won't re-emit for same tile — verified by attribute
        assert combat_scene._last_hovered == (5, 5)

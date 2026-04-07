"""Tests for ZoneDetailWidget."""

import pytest
from PyQt5.QtWidgets import QPushButton
from ui.exploration.zone_detail_widget import ZoneDetailWidget
from models.exploration.zone_scene_data import ZoneSceneData, SceneObject, NavArrow


def _make_scene(num_npcs=2, num_arrows=2, locked_arrows=0):
    objects = {1: [], 2: [], 3: []}
    for i in range(num_npcs):
        objects[3].append(SceneObject(
            name=f"NPC_{i}", obj_type="npc", depth=3,
            x_percent=0.3 + i * 0.2, faction="friendly",
            initials=f"N{i}", interaction_types=["talk", "inspect"],
        ))
    arrows = []
    for i in range(num_arrows):
        arrows.append(NavArrow(
            target_zone_id=f"zone_{i}", target_label=f"Room {i}",
            direction="left" if i % 2 == 0 else "right",
            locked=i < locked_arrows,
            lock_description=f"DC 15" if i < locked_arrows else "",
        ))
    return ZoneSceneData(
        zone_id="test", zone_label="Test Zone",
        zone_description="A test zone.",
        objects_by_depth=objects, nav_arrows=arrows,
    )


class TestZoneDetailWidget:

    def test_creates(self, qapp):
        w = ZoneDetailWidget(role="player")
        assert w is not None

    def test_load_zone_sets_label(self, qapp):
        w = ZoneDetailWidget()
        w.load_zone(_make_scene())
        assert w._breadcrumb_bar._zone_label.text() == "Test Zone"

    def test_nav_arrows_created(self, qapp):
        w = ZoneDetailWidget()
        w.load_zone(_make_scene(num_arrows=3))
        nav_btns = [b for b, _d in w._nav_overlay._buttons
                    if isinstance(b, QPushButton)]
        assert len(nav_btns) == 3

    def test_locked_arrow_disabled(self, qapp):
        w = ZoneDetailWidget()
        w.load_zone(_make_scene(num_arrows=2, locked_arrows=1))
        disabled = [b for b, _d in w._nav_overlay._buttons if not b.isEnabled()]
        assert len(disabled) >= 1

    def test_navigate_signal(self, qapp):
        w = ZoneDetailWidget()
        w.load_zone(_make_scene(num_arrows=1))
        signals = []
        w.navigate_to_zone.connect(lambda zid: signals.append(zid))
        for btn, _d in w._nav_overlay._buttons:
            if isinstance(btn, QPushButton) and btn.isEnabled():
                btn.click()
                break
        assert len(signals) == 1

    def test_map_button_signal(self, qapp):
        w = ZoneDetailWidget()
        signals = []
        w.navigate_to_map.connect(lambda: signals.append(True))
        w._breadcrumb_bar._map_btn.click()
        assert len(signals) == 1

    def test_entity_clicked_signal(self, qapp):
        w = ZoneDetailWidget()
        signals = []
        w.entity_clicked.connect(lambda n: signals.append(n))
        w._canvas.entity_clicked.emit("NPC_0")
        assert signals == ["NPC_0"]

    def test_entity_list_accessor(self, qapp):
        """Public entity_list property points to sidebar list."""
        w = ZoneDetailWidget()
        assert w.entity_list is w._entity_sidebar._entity_list

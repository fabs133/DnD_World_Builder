"""Tests for zone scene data model and builder."""

import pytest
from models.tiles.tile_zone import TileZone, ZonePlacement
from models.entities.game_entity import GameEntity
from models.exploration.zone_scene_data import build_zone_scene, _get_initials, _infer_direction


class FakeEntity:
    def __init__(self, name, entity_type="npc"):
        self.name = name
        self.entity_type = entity_type

    def to_dict(self):
        return {"name": self.name, "entity_type": self.entity_type}


class TestZonePlacement:

    def test_defaults(self):
        entity = FakeEntity("Guard")
        p = ZonePlacement(entity=entity)
        assert p.depth == 3
        assert p.x_percent == 0.5
        assert p.interaction_types == ["inspect"]

    def test_roundtrip(self):
        entity = GameEntity("Marta", "npc")
        p = ZonePlacement(entity=entity, depth=2, x_percent=0.7,
                          interaction_types=["talk", "trade"])
        data = p.to_dict()
        restored = ZonePlacement.from_dict(data)
        assert restored.depth == 2
        assert restored.x_percent == 0.7
        assert "talk" in restored.interaction_types


class TestBuildZoneScene:

    def _make_zones(self):
        z1 = TileZone(zone_id="entrance", label="Entrance", connections=["main_hall"])
        z2 = TileZone(zone_id="main_hall", label="Main Hall",
                      connections=["entrance", "upstairs"],
                      description="A large hall.")
        z3 = TileZone(zone_id="upstairs", label="Upstairs Rooms",
                      connections=["main_hall"], locked=True, lock_dc=15)
        return {"entrance": z1, "main_hall": z2, "upstairs": z3}

    def test_empty_zone(self):
        zone = TileZone(zone_id="empty", label="Empty Room")
        scene = build_zone_scene(zone, {"empty": zone})
        assert all(len(v) == 0 for v in scene.objects_by_depth.values())

    def test_entities_sorted_by_depth(self):
        zone = TileZone(zone_id="z", label="Z", placements=[
            ZonePlacement(entity=FakeEntity("Far"), depth=1, x_percent=0.3),
            ZonePlacement(entity=FakeEntity("Near"), depth=3, x_percent=0.7),
            ZonePlacement(entity=FakeEntity("Mid"), depth=2, x_percent=0.5),
        ])
        scene = build_zone_scene(zone, {"z": zone})
        assert len(scene.objects_by_depth[1]) == 1
        assert scene.objects_by_depth[1][0].name == "Far"
        assert len(scene.objects_by_depth[3]) == 1
        assert scene.objects_by_depth[3][0].name == "Near"

    def test_nav_arrows(self):
        zones = self._make_zones()
        scene = build_zone_scene(zones["main_hall"], zones)
        assert len(scene.nav_arrows) == 2

    def test_locked_connection(self):
        zones = self._make_zones()
        scene = build_zone_scene(zones["main_hall"], zones)
        upstairs_arrow = next(a for a in scene.nav_arrows if a.target_zone_id == "upstairs")
        assert upstairs_arrow.locked is True
        assert "15" in upstairs_arrow.lock_description

    def test_player_identified(self):
        zone = TileZone(zone_id="z", label="Z", placements=[
            ZonePlacement(entity=FakeEntity("Hero", "player"), depth=3),
            ZonePlacement(entity=FakeEntity("Guard", "npc"), depth=2),
        ])
        scene = build_zone_scene(zone, {"z": zone}, player_entity_name="Hero")
        assert scene.player_position is not None
        # Hero should not be in objects_by_depth (rendered separately)
        all_names = [o.name for objs in scene.objects_by_depth.values() for o in objs]
        assert "Hero" not in all_names

    def test_faction_from_entity_type(self):
        zone = TileZone(zone_id="z", label="Z", placements=[
            ZonePlacement(entity=FakeEntity("Goblin", "enemy"), depth=3),
        ])
        scene = build_zone_scene(zone, {"z": zone})
        assert scene.objects_by_depth[3][0].faction == "hostile"

    def test_arrow_direction_stairs(self):
        zones = self._make_zones()
        scene = build_zone_scene(zones["main_hall"], zones)
        upstairs_arrow = next(a for a in scene.nav_arrows if a.target_zone_id == "upstairs")
        assert upstairs_arrow.direction == "up"


class TestInitials:
    def test_single_word(self):
        assert _get_initials("Marta") == "M"

    def test_two_words(self):
        assert _get_initials("Guard Captain") == "GC"


class TestInferDirection:
    def test_upstairs(self):
        assert _infer_direction("Upstairs Rooms", 0) == "up"

    def test_cellar(self):
        assert _infer_direction("Wine Cellar", 0) == "down"

    def test_default_alternating(self):
        assert _infer_direction("Main Hall", 0) == "left"
        assert _infer_direction("Back Room", 1) == "right"


class TestBackwardCompat:
    def test_old_zone_without_placements(self):
        data = {
            "zone_id": "old",
            "label": "Old Zone",
            "connections": [],
        }
        zone = TileZone.from_dict(data)
        assert zone.placements == []

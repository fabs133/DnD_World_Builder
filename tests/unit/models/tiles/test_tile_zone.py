"""Tests for TileZone data model."""

from models.tiles.tile_zone import TileZone


class TestTileZone:

    def test_zone_creation_defaults(self):
        zone = TileZone(zone_id="entrance", label="Entrance")
        assert zone.zone_id == "entrance"
        assert zone.label == "Entrance"
        assert zone.description is None
        assert zone.connections == []
        assert zone.locked is False
        assert zone.lock_dc == 15
        assert zone.tags == []
        assert zone.encounter_template_id is None

    def test_zone_serialization_roundtrip(self):
        zone = TileZone(
            zone_id="bar",
            label="Bar Area",
            description="A crowded tavern bar.",
            connections=["entrance", "back_room"],
            locked=False,
            tags=["social", "shop"],
        )
        data = zone.to_dict()
        restored = TileZone.from_dict(data)
        assert restored.zone_id == zone.zone_id
        assert restored.label == zone.label
        assert restored.description == zone.description
        assert restored.connections == zone.connections
        assert restored.tags == zone.tags

    def test_zone_locked_roundtrip(self):
        zone = TileZone(
            zone_id="vault",
            label="Vault",
            locked=True,
            lock_dc=20,
        )
        data = zone.to_dict()
        restored = TileZone.from_dict(data)
        assert restored.locked is True
        assert restored.lock_dc == 20

    def test_zone_with_encounter_template(self):
        zone = TileZone(
            zone_id="ambush",
            label="Ambush Point",
            encounter_template_id="tmpl_001",
        )
        data = zone.to_dict()
        restored = TileZone.from_dict(data)
        assert restored.encounter_template_id == "tmpl_001"

    def test_zone_connections_list(self):
        zone = TileZone(
            zone_id="a",
            label="Room A",
            connections=["b", "c", "d"],
        )
        assert len(zone.connections) == 3
        data = zone.to_dict()
        assert data["connections"] == ["b", "c", "d"]

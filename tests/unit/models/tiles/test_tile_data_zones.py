"""Tests for TileData zone integration."""

from models.tiles.tile_data import TileData, TerrainType
from models.tiles.tile_zone import TileZone


class TestTileDataZones:

    def test_tile_without_zones_backward_compat(self):
        """Existing TileData works without zones."""
        td = TileData(position=(1, 2), terrain=TerrainType.FLOOR)
        assert td.has_zones is False
        assert td.zones == []

        data = td.to_dict()
        assert "zones" not in data  # not serialized when empty

        restored = TileData.from_dict(data)
        assert restored.has_zones is False

    def test_tile_with_zones_roundtrip(self):
        """TileData with zones serializes and deserializes correctly."""
        zones = [
            TileZone(zone_id="entrance", label="Entrance", connections=["bar"]),
            TileZone(zone_id="bar", label="Bar", connections=["entrance", "back"]),
        ]
        td = TileData(position=(0, 0), terrain=TerrainType.FLOOR, zones=zones)
        assert td.has_zones is True

        data = td.to_dict()
        assert "zones" in data
        assert len(data["zones"]) == 2

        restored = TileData.from_dict(data)
        assert restored.has_zones is True
        assert len(restored.zones) == 2
        assert restored.zones[0].zone_id == "entrance"
        assert restored.zones[1].connections == ["entrance", "back"]

    def test_has_zones_property(self):
        td_empty = TileData(position=(0, 0), terrain=TerrainType.FLOOR)
        assert td_empty.has_zones is False

        td_with = TileData(
            position=(0, 0),
            terrain=TerrainType.FLOOR,
            zones=[TileZone(zone_id="a", label="A")],
        )
        assert td_with.has_zones is True

    def test_loading_legacy_json_without_zones(self):
        """Old JSON without 'zones' key loads without error."""
        legacy_data = {
            "tile_id": "old_tile",
            "position": [3, 4],
            "terrain": "FLOOR",
            "tags": [],
            "entities": [],
            "triggers": [],
        }
        td = TileData.from_dict(legacy_data)
        assert td.has_zones is False
        assert td.zones == []
        assert td.position == (3, 4)

import pytest
from models.templates.zone_template import ZoneTemplate


def _sample_zones_data():
    return [
        {
            "zone_id": "room_a",
            "label": "Room A",
            "description": "A dusty room.",
            "background_image": None,
            "connections": ["room_b"],
            "locked": False,
            "lock_dc": 15,
            "tags": ["indoor"],
            "encounter_template_id": None,
        },
        {
            "zone_id": "room_b",
            "label": "Room B",
            "description": "A brighter room.",
            "background_image": None,
            "connections": ["room_a"],
            "locked": True,
            "lock_dc": 20,
            "tags": ["indoor", "locked"],
            "encounter_template_id": None,
        },
    ]


def _sample_template():
    return ZoneTemplate(
        template_id="test_dungeon",
        name="Test Dungeon",
        zones_data=_sample_zones_data(),
        tags=["dungeon", "test"],
        description="A two-room dungeon for testing.",
    )


class TestZoneTemplate:
    def test_serialization_roundtrip(self):
        original = _sample_template()
        data = original.to_dict()
        restored = ZoneTemplate.from_dict(data)

        assert restored.template_id == original.template_id
        assert restored.name == original.name
        assert restored.zones_data == original.zones_data
        assert restored.tags == original.tags
        assert restored.description == original.description

    def test_to_zones_dicts_is_deep_copy(self):
        template = _sample_template()
        zones = template.to_zones_dicts()

        # Mutate the returned list
        zones[0]["label"] = "MUTATED"
        zones.pop()

        # Original template should be unchanged
        assert template.zones_data[0]["label"] == "Room A"
        assert len(template.zones_data) == 2

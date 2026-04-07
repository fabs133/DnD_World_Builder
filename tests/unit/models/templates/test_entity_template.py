import pytest
from models.templates.entity_template import EntityTemplate


def _sample_entity_data():
    return {
        "name": "Test NPC",
        "entity_type": "npc",
        "stats": {"str": 10, "dex": 12, "con": 10, "int": 14, "wis": 13, "cha": 11, "ac": 12, "hp": 8, "max_hp": 8},
        "inventory": ["Dagger"],
        "triggers": [],
        "hp": 8,
        "max_hp": 8,
        "conditions": [],
    }


def _sample_template():
    return EntityTemplate(
        template_id="test_npc",
        name="Test NPC",
        category="npc",
        entity_data=_sample_entity_data(),
        tags=["test", "npc"],
        description="A template used for testing.",
    )


class TestEntityTemplate:
    def test_serialization_roundtrip(self):
        original = _sample_template()
        data = original.to_dict()
        restored = EntityTemplate.from_dict(data)

        assert restored.template_id == original.template_id
        assert restored.name == original.name
        assert restored.category == original.category
        assert restored.entity_data == original.entity_data
        assert restored.tags == original.tags
        assert restored.description == original.description

    def test_to_entity_dict_is_deep_copy(self):
        template = _sample_template()
        entity_dict = template.to_entity_dict()

        # Mutate the returned dict
        entity_dict["name"] = "MUTATED"
        entity_dict["stats"]["str"] = 99

        # Original template should be unchanged
        assert template.entity_data["name"] == "Test NPC"
        assert template.entity_data["stats"]["str"] == 10

    def test_from_dict_missing_optional_fields(self):
        data = {
            "template_id": "minimal",
            "name": "Minimal",
            "category": "enemy",
            "entity_data": {"name": "Minimal", "entity_type": "enemy"},
        }
        tmpl = EntityTemplate.from_dict(data)
        assert tmpl.tags == []
        assert tmpl.description == ""
        assert tmpl.is_builtin is False

    def test_from_entity(self):
        class FakeEntity:
            def to_dict(self):
                return {
                    "name": "Goblin Scout",
                    "entity_type": "enemy",
                    "stats": {"str": 8, "dex": 14},
                    "hp": 7,
                    "max_hp": 7,
                }

        entity = FakeEntity()
        tmpl = EntityTemplate.from_entity(
            entity,
            template_id="goblin_scout",
            tags=["monster"],
            description="A sneaky goblin.",
        )

        assert tmpl.template_id == "goblin_scout"
        assert tmpl.name == "Goblin Scout"
        assert tmpl.category == "enemy"
        assert tmpl.entity_data["stats"]["dex"] == 14
        assert tmpl.tags == ["monster"]
        assert tmpl.description == "A sneaky goblin."

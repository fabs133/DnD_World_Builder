import json
import tempfile
from pathlib import Path

import pytest

from core.template_registry import TemplateRegistry
from models.templates.entity_template import EntityTemplate
from models.templates.zone_template import ZoneTemplate


@pytest.fixture
def registry():
    reg = TemplateRegistry()
    reg.load_builtins()
    return reg


class TestTemplateRegistry:
    def test_load_builtins_finds_templates(self, registry):
        entities = registry.get_entity_templates()
        zones = registry.get_zone_templates()
        assert len(entities) >= 5, f"Expected at least 5 entity templates, got {len(entities)}"
        assert len(zones) >= 2, f"Expected at least 2 zone templates, got {len(zones)}"

    def test_search_by_name(self, registry):
        results = registry.search("guard")
        names = [t.name for t in results["entities"]]
        assert "Guard" in names
        assert "Guard Captain" in names

    def test_filter_by_category(self, registry):
        enemies = registry.get_entity_templates(category="enemy")
        names = {t.name for t in enemies}
        assert "Goblin" in names
        assert "Wolf" in names
        # NPCs should not appear
        for t in enemies:
            assert t.category == "enemy"

    def test_save_user_template(self):
        reg = TemplateRegistry()
        tmpl = EntityTemplate(
            template_id="custom_bandit",
            name="Bandit",
            category="enemy",
            entity_data={"name": "Bandit", "entity_type": "enemy", "stats": {"str": 11}, "hp": 11, "max_hp": 11},
            tags=["humanoid"],
            description="A common bandit.",
        )

        with tempfile.TemporaryDirectory() as tmp:
            reg.save_user_template(tmpl, tmp)
            saved_path = Path(tmp) / "_templates" / "entities" / "custom_bandit.json"
            assert saved_path.exists()

            data = json.loads(saved_path.read_text(encoding="utf-8"))
            assert data["template_id"] == "custom_bandit"
            assert data["name"] == "Bandit"

            # Verify template is in-memory
            found = reg.get_entity_templates(category="enemy")
            assert any(t.template_id == "custom_bandit" for t in found)

            # Load into a fresh registry to verify the file is correct
            reg2 = TemplateRegistry()
            reg2.load_user_templates(tmp)
            found2 = reg2.get_entity_templates(category="enemy")
            assert any(t.template_id == "custom_bandit" for t in found2)

    def test_delete_user_template(self):
        reg = TemplateRegistry()
        tmpl = EntityTemplate(
            template_id="to_delete",
            name="Delete Me",
            category="npc",
            entity_data={"name": "Delete Me", "entity_type": "npc"},
            tags=["temp"],
            description="Will be deleted.",
        )

        with tempfile.TemporaryDirectory() as tmp:
            reg.save_user_template(tmpl, tmp)
            saved_path = Path(tmp) / "_templates" / "entities" / "to_delete.json"
            assert saved_path.exists()

            reg.delete_user_template("to_delete", tmp)
            assert not saved_path.exists()
            assert not any(t.template_id == "to_delete" for t in reg.get_entity_templates())

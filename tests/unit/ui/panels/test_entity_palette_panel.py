"""Tests for EntityPalettePanel."""

import pytest
from ui.panels.entity_palette_panel import EntityPalettePanel, QUICK_TEMPLATES


class TestEntityPalettePanel:

    def test_creates(self, qapp):
        panel = EntityPalettePanel()
        assert panel is not None

    def test_quick_templates_present(self, qapp):
        panel = EntityPalettePanel()
        assert panel._template_list.count() == len(QUICK_TEMPLATES)

    def test_search_filters(self, qapp):
        panel = EntityPalettePanel()
        panel._on_search("guard")
        visible = sum(1 for i in range(panel._template_list.count())
                      if not panel._template_list.item(i).isHidden())
        assert visible >= 1

    def test_search_empty_shows_all(self, qapp):
        panel = EntityPalettePanel()
        panel._on_search("xyz_nonexistent")
        panel._on_search("")
        visible = sum(1 for i in range(panel._template_list.count())
                      if not panel._template_list.item(i).isHidden())
        assert visible == len(QUICK_TEMPLATES)

    def test_scenario_entities(self, qapp):
        class FakeEntity:
            name = "Marta"
            def to_dict(self): return {"name": "Marta", "entity_type": "npc"}

        panel = EntityPalettePanel(scenario_entities=[FakeEntity(), FakeEntity()])
        assert panel._scenario_list.count() == 2

    def test_refresh_scenario(self, qapp):
        panel = EntityPalettePanel()
        assert panel._scenario_list.count() == 0

        class FakeEntity:
            name = "Guard"
            def to_dict(self): return {"name": "Guard", "entity_type": "npc"}

        panel.refresh_scenario_entities([FakeEntity()])
        assert panel._scenario_list.count() == 1

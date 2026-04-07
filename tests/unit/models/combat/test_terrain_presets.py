"""Tests for built-in terrain presets."""

from models.combat.terrain_presets import (
    TERRAIN_PRESETS, get_preset, list_presets, register_preset,
)
from models.combat.encounter_template import TerrainPreset


class TestTerrainPresets:

    def test_builtin_presets_registered(self):
        """At least 5 built-in presets exist."""
        assert len(TERRAIN_PRESETS) >= 5

    def test_get_preset_returns_correct_type(self):
        preset = get_preset("forest")
        assert isinstance(preset, TerrainPreset)
        assert preset.preset_id == "forest"

    def test_get_preset_unknown_returns_none(self):
        assert get_preset("nonexistent") is None

    def test_forest_preset_has_trees(self):
        preset = get_preset("forest")
        labels = [o.get("label", "") for o in preset.obstacles]
        assert "Tree" in labels

    def test_tavern_preset_has_tables(self):
        preset = get_preset("tavern")
        labels = [o.get("label", "") for o in preset.obstacles]
        assert "Table" in labels

    def test_dungeon_preset_has_pillars(self):
        preset = get_preset("dungeon")
        labels = [o.get("label", "") for o in preset.obstacles]
        assert "Stone Pillar" in labels

    def test_list_presets_returns_all(self):
        presets = list_presets()
        ids = {p.preset_id for p in presets}
        assert "forest" in ids
        assert "cave" in ids
        assert "open_field" in ids

    def test_register_custom_preset(self):
        custom = TerrainPreset(preset_id="test_custom", name="Custom Test")
        register_preset(custom)
        assert get_preset("test_custom") is custom
        # Clean up
        del TERRAIN_PRESETS["test_custom"]

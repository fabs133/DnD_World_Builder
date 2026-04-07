from ui.animations.config import ParticleCategory, ParticlePreset
from ui.animations.presets import PRESETS, CONDITION_PRESETS, get_preset, get_presets_by_category

class TestPresetsRegistry:
    def test_all_presets_have_unique_names(self):
        names = [p.name for p in PRESETS.values()]
        assert len(names) == len(set(names))

    def test_all_presets_valid_category(self):
        for p in PRESETS.values():
            assert isinstance(p.category, ParticleCategory)

    def test_all_categories_have_presets(self):
        for cat in ParticleCategory:
            presets = get_presets_by_category(cat)
            assert len(presets) >= 1, f"No presets for {cat.name}"

    def test_get_preset_found(self):
        p = get_preset("slash_sparks")
        assert p is not None
        assert p.name == "slash_sparks"

    def test_get_preset_not_found(self):
        assert get_preset("nonexistent") is None

    def test_condition_presets_valid(self):
        for condition, preset_name in CONDITION_PRESETS.items():
            assert preset_name in PRESETS, f"Condition '{condition}' maps to missing preset '{preset_name}'"

    def test_no_zero_lifetime(self):
        for p in PRESETS.values():
            assert p.lifetime_ms > 0, f"Preset '{p.name}' has zero lifetime"

    def test_no_zero_count(self):
        for p in PRESETS.values():
            assert p.count > 0, f"Preset '{p.name}' has zero count"

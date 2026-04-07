import pytest
from ui.animations.config import (
    ParticleCategory, EmissionShape, ParticleMotion,
    ParticlePreset, AnimationType, AnimationConfig, AttackAnimConfig,
    DEFAULT_MELEE_ATTACK, DEFAULT_RANGED_ATTACK, DEFAULT_SPELL_ATTACK,
)

class TestParticleCategory:
    def test_has_exactly_6_members(self):
        assert len(ParticleCategory) == 6

    def test_all_members_present(self):
        names = {m.name for m in ParticleCategory}
        assert names == {"IMPACT", "AMBIENT", "TRAIL", "RADIANT", "STATUS", "GAME"}

class TestEnums:
    def test_emission_shape_count(self):
        assert len(EmissionShape) == 5

    def test_particle_motion_count(self):
        assert len(ParticleMotion) == 7

    def test_animation_type_count(self):
        assert len(AnimationType) == 6

class TestParticlePreset:
    def test_defaults_valid(self):
        p = ParticlePreset(name="test", category=ParticleCategory.IMPACT)
        assert p.lifetime_ms > 0
        assert 0 <= p.opacity_start <= 1
        assert 0 <= p.opacity_end <= 1
        assert p.count > 0

    def test_frozen(self):
        p = ParticlePreset(name="test", category=ParticleCategory.IMPACT)
        with pytest.raises(AttributeError):
            p.name = "changed"

class TestAttackAnimConfig:
    def test_defaults_have_preset(self):
        assert DEFAULT_MELEE_ATTACK.impact_preset
        assert DEFAULT_RANGED_ATTACK.impact_preset
        assert DEFAULT_SPELL_ATTACK.impact_preset

    def test_configs_distinct(self):
        assert DEFAULT_MELEE_ATTACK.impact_preset != DEFAULT_RANGED_ATTACK.impact_preset
        assert DEFAULT_MELEE_ATTACK.impact_preset != DEFAULT_SPELL_ATTACK.impact_preset

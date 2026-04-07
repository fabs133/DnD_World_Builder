import pytest
from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QGraphicsScene

from ui.animations.config import ParticlePreset, ParticleCategory, ParticleMotion, EmissionShape
from ui.animations.particle_item import ParticleItem
from ui.animations.presets import PRESETS, get_preset


BURST_PRESET = ParticlePreset(
    name="test_burst",
    category=ParticleCategory.IMPACT,
    count=5,
    emission_rate=0.0,  # burst mode
    lifetime_ms=100,
    lifetime_variance_ms=0,
)

CONTINUOUS_PRESET = ParticlePreset(
    name="test_continuous",
    category=ParticleCategory.AMBIENT,
    count=5,
    emission_rate=10.0,
    lifetime_ms=200,
    lifetime_variance_ms=0,
)


class TestParticleItemCreation:
    def test_creates_with_preset(self, qapp):
        item = ParticleItem(BURST_PRESET, QPointF(10, 20))
        assert item is not None

    def test_position_set(self, qapp):
        item = ParticleItem(BURST_PRESET, QPointF(100, 200))
        assert item.pos().x() == 100
        assert item.pos().y() == 200

    def test_z_value_from_preset(self, qapp):
        item = ParticleItem(BURST_PRESET)
        assert item.zValue() == BURST_PRESET.layer

    def test_bounding_rect_nonzero(self, qapp):
        item = ParticleItem(BURST_PRESET)
        br = item.boundingRect()
        assert br.width() > 0
        assert br.height() > 0

    def test_creates_with_any_real_preset(self, qapp):
        """Verify ParticleItem can be created with every registered preset."""
        for name, preset in PRESETS.items():
            item = ParticleItem(preset)
            assert item is not None, f"Failed for preset '{name}'"


class TestBurstMode:
    def test_burst_spawns_particles_on_start(self, qapp):
        item = ParticleItem(BURST_PRESET)
        item.start()
        assert len(item._particles) == BURST_PRESET.count
        item._timer.stop()

    def test_burst_not_emitting_after_start(self, qapp):
        item = ParticleItem(BURST_PRESET)
        item.start()
        assert not item._emitting
        item._timer.stop()

    def test_burst_self_removes_from_scene(self, qapp):
        scene = QGraphicsScene()
        item = ParticleItem(BURST_PRESET)
        scene.addItem(item)
        item.start()
        # Simulate enough ticks for all particles to die
        for _ in range(20):
            item._update()
        assert item not in scene.items()


class TestContinuousMode:
    def test_continuous_emits_over_time(self, qapp):
        item = ParticleItem(CONTINUOUS_PRESET)
        item.start()
        assert item._emitting
        # Run a few ticks
        for _ in range(5):
            item._update()
        assert len(item._particles) > 0
        item.stop()
        item._timer.stop()

    def test_stop_halts_emission(self, qapp):
        item = ParticleItem(CONTINUOUS_PRESET)
        item.start()
        item.stop()
        assert not item._emitting

    def test_is_alive_while_emitting(self, qapp):
        item = ParticleItem(CONTINUOUS_PRESET)
        item.start()
        assert item.is_alive()
        item.stop()
        item._timer.stop()

    def test_is_alive_with_particles(self, qapp):
        item = ParticleItem(CONTINUOUS_PRESET)
        item.start()
        # Run a few ticks so particles are actually emitted
        for _ in range(5):
            item._update()
        item.stop()
        # Still has living particles even though emission stopped
        assert len(item._particles) > 0
        assert item.is_alive()
        item._timer.stop()


class TestSetCenter:
    def test_updates_position(self, qapp):
        item = ParticleItem(BURST_PRESET, QPointF(0, 0))
        item.set_center(QPointF(99, 88))
        assert item.pos().x() == 99
        assert item.pos().y() == 88


class TestMotionTypes:
    """Smoke-test each motion type doesn't crash during update."""

    @pytest.mark.parametrize("motion", list(ParticleMotion))
    def test_motion_no_crash(self, qapp, motion):
        preset = ParticlePreset(
            name=f"test_{motion.name}",
            category=ParticleCategory.IMPACT,
            count=3,
            emission_rate=0.0,
            motion=motion,
            emission_shape=EmissionShape.DISC,
            emission_radius=10.0,
            lifetime_ms=100,
        )
        item = ParticleItem(preset)
        item.start()
        for _ in range(5):
            item._update()
        item._timer.stop()

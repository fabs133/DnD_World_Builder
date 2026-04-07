import pytest
from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QGraphicsScene

from ui.animations.effect_overlay import SlashEffect, GlowRing


class TestSlashEffect:
    def test_creates_without_error(self, qapp):
        effect = SlashEffect(QPointF(50, 50))
        assert effect is not None

    def test_adds_to_scene(self, qapp):
        scene = QGraphicsScene()
        effect = SlashEffect(QPointF(10, 10))
        scene.addItem(effect)
        assert effect in scene.items()

    def test_bounding_rect_nonzero(self, qapp):
        effect = SlashEffect(QPointF(0, 0), size=30)
        br = effect.boundingRect()
        assert br.width() > 0
        assert br.height() > 0

    def test_play_starts_timer(self, qapp):
        effect = SlashEffect(QPointF(0, 0))
        effect.play()
        assert effect._timer.isActive()
        effect._timer.stop()

    def test_self_removes_after_duration(self, qapp):
        scene = QGraphicsScene()
        effect = SlashEffect(QPointF(0, 0), duration_ms=100)
        scene.addItem(effect)
        effect.play()
        for _ in range(20):
            effect._tick()
        assert effect not in scene.items()

    def test_z_value_set(self, qapp):
        effect = SlashEffect(QPointF(0, 0))
        assert effect.zValue() == 998

    def test_custom_color(self, qapp):
        effect = SlashEffect(QPointF(0, 0), color="#ff0000")
        assert effect._color.name() == "#ff0000"


class TestGlowRing:
    def test_creates_without_error(self, qapp):
        ring = GlowRing(QPointF(50, 50))
        assert ring is not None

    def test_adds_to_scene(self, qapp):
        scene = QGraphicsScene()
        ring = GlowRing(QPointF(10, 10))
        scene.addItem(ring)
        assert ring in scene.items()

    def test_bounding_rect_nonzero(self, qapp):
        ring = GlowRing(QPointF(0, 0), max_radius=25)
        br = ring.boundingRect()
        assert br.width() > 0
        assert br.height() > 0

    def test_play_starts_timer(self, qapp):
        ring = GlowRing(QPointF(0, 0))
        ring.play()
        assert ring._timer.isActive()
        ring._timer.stop()

    def test_self_removes_after_duration(self, qapp):
        scene = QGraphicsScene()
        ring = GlowRing(QPointF(0, 0), duration_ms=100)
        scene.addItem(ring)
        ring.play()
        for _ in range(20):
            ring._tick()
        assert ring not in scene.items()

    def test_radius_grows_during_animation(self, qapp):
        ring = GlowRing(QPointF(0, 0), max_radius=30, duration_ms=200)
        ring.play()
        ring._tick()
        assert ring._current_radius > 0

    def test_opacity_decreases_during_animation(self, qapp):
        ring = GlowRing(QPointF(0, 0), duration_ms=200)
        ring.play()
        ring._tick()
        assert ring._opacity < 0.8

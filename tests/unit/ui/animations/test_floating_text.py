import pytest
from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QGraphicsScene

from ui.animations.floating_text import FloatingText


class TestFloatingText:
    def test_creates_with_correct_text(self, qapp):
        ft = FloatingText("42", QPointF(0, 0))
        assert ft.toPlainText() == "42"

    def test_color_applied(self, qapp):
        ft = FloatingText("-10", QPointF(0, 0), color="#ff0000")
        assert ft.defaultTextColor().name() == "#ff0000"

    def test_initial_position(self, qapp):
        ft = FloatingText("MISS", QPointF(50, 100))
        assert ft.pos().x() == 50
        assert ft.pos().y() == 100

    def test_z_value_is_high(self, qapp):
        ft = FloatingText("1", QPointF(0, 0))
        assert ft.zValue() >= 1000

    def test_adds_to_scene(self, qapp):
        scene = QGraphicsScene()
        ft = FloatingText("hit", QPointF(10, 20))
        scene.addItem(ft)
        assert ft in scene.items()

    def test_play_starts_timer(self, qapp):
        ft = FloatingText("5", QPointF(0, 0), duration_ms=500)
        ft.play()
        assert ft._timer.isActive()
        ft._timer.stop()

    def test_self_removes_after_duration(self, qapp):
        scene = QGraphicsScene()
        ft = FloatingText("bye", QPointF(0, 0), duration_ms=100)
        scene.addItem(ft)
        ft.play()
        # Simulate enough ticks to exceed duration
        for _ in range(10):
            ft._tick()
        # Should have removed itself
        assert ft not in scene.items()

    def test_opacity_decreases_during_animation(self, qapp):
        ft = FloatingText("fade", QPointF(0, 0), duration_ms=200)
        ft.play()
        ft._tick()  # One tick
        assert ft.opacity() < 1.0

    def test_position_rises_during_animation(self, qapp):
        ft = FloatingText("rise", QPointF(0, 100), duration_ms=200)
        ft.play()
        ft._tick()
        assert ft.pos().y() < 100

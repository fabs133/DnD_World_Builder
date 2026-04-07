import pytest
from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsRectItem

from ui.animations.token_animator import TokenAnimator


class MockTile(QGraphicsRectItem):
    """Minimal tile mock for animation tests."""
    def __init__(self):
        super().__init__(0, 0, 40, 40)


class TestLunge:
    def test_no_crash_on_zero_distance(self, qapp):
        tile = MockTile()
        tile.setPos(50, 50)
        called = [False]
        TokenAnimator.lunge(tile, QPointF(50, 50), callback=lambda: called.__setitem__(0, True))
        # Zero distance triggers immediate callback
        assert called[0]

    def test_returns_to_origin(self, qapp):
        scene = QGraphicsScene()
        tile = MockTile()
        tile.setPos(50, 50)
        scene.addItem(tile)
        origin = QPointF(tile.pos())

        TokenAnimator.lunge(tile, QPointF(200, 200), duration_ms=100)
        # Simulate ticks until done
        timer = tile._anim_timer
        for _ in range(20):
            timer.timeout.emit()
        assert abs(tile.pos().x() - origin.x()) < 1
        assert abs(tile.pos().y() - origin.y()) < 1

    def test_callback_fires(self, qapp):
        scene = QGraphicsScene()
        tile = MockTile()
        tile.setPos(0, 0)
        scene.addItem(tile)
        called = [False]

        TokenAnimator.lunge(tile, QPointF(100, 0), duration_ms=80,
                            callback=lambda: called.__setitem__(0, True))
        timer = tile._anim_timer
        for _ in range(20):
            timer.timeout.emit()
        assert called[0]


class TestShake:
    def test_no_crash(self, qapp):
        tile = MockTile()
        tile.setPos(10, 10)
        TokenAnimator.shake(tile, duration_ms=100)
        # Just verify it doesn't raise

    def test_returns_to_origin(self, qapp):
        scene = QGraphicsScene()
        tile = MockTile()
        tile.setPos(30, 30)
        scene.addItem(tile)

        TokenAnimator.shake(tile, duration_ms=80)
        timer = tile._anim_timer
        for _ in range(20):
            timer.timeout.emit()
        assert abs(tile.pos().x() - 30) < 1
        assert abs(tile.pos().y() - 30) < 1

    def test_callback_fires(self, qapp):
        tile = MockTile()
        tile.setPos(0, 0)
        called = [False]
        TokenAnimator.shake(tile, duration_ms=80,
                            callback=lambda: called.__setitem__(0, True))
        timer = tile._anim_timer
        for _ in range(20):
            timer.timeout.emit()
        assert called[0]


class TestRecoil:
    def test_no_crash(self, qapp):
        tile = MockTile()
        tile.setPos(50, 50)
        TokenAnimator.recoil(tile, QPointF(0, 0), duration_ms=100)

    def test_returns_to_origin(self, qapp):
        scene = QGraphicsScene()
        tile = MockTile()
        tile.setPos(50, 50)
        scene.addItem(tile)

        TokenAnimator.recoil(tile, QPointF(0, 0), duration_ms=80)
        timer = tile._anim_timer
        for _ in range(20):
            timer.timeout.emit()
        assert abs(tile.pos().x() - 50) < 1
        assert abs(tile.pos().y() - 50) < 1

    def test_callback_fires(self, qapp):
        tile = MockTile()
        tile.setPos(50, 50)
        called = [False]
        TokenAnimator.recoil(tile, QPointF(0, 0), duration_ms=80,
                             callback=lambda: called.__setitem__(0, True))
        timer = tile._anim_timer
        for _ in range(20):
            timer.timeout.emit()
        assert called[0]

    def test_zero_distance_no_crash(self, qapp):
        tile = MockTile()
        tile.setPos(50, 50)
        # Source is at same position — should handle gracefully
        TokenAnimator.recoil(tile, QPointF(50, 50), duration_ms=100)

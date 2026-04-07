"""Tests for MeasureMode two-click measurement."""

import pytest
from unittest.mock import MagicMock

from models.world.world_tile_manager import WorldTileManager
from ui.tools.measure_overlay import MeasureOverlay
from ui.tools.measure_mode import MeasureMode
from PyQt5.QtWidgets import QGraphicsScene


@pytest.fixture
def scene():
    return QGraphicsScene()


@pytest.fixture
def tile_map():
    return WorldTileManager(5, 5, tile_type="square")


@pytest.fixture
def overlay(scene):
    return MeasureOverlay(scene, tile_size=50)


@pytest.fixture
def status_bar():
    sb = MagicMock()
    sb.showMessage = MagicMock()
    return sb


@pytest.fixture
def mode(scene, tile_map, overlay, status_bar):
    return MeasureMode(scene, tile_map, overlay, status_bar)


class TestMeasureModeToggle:

    def test_starts_inactive(self, mode):
        assert mode.active is False

    def test_toggle_activates(self, mode):
        mode.toggle()
        assert mode.active is True

    def test_toggle_twice_deactivates(self, mode):
        mode.toggle()
        mode.toggle()
        assert mode.active is False

    def test_inactive_ignores_clicks(self, mode):
        consumed = mode.on_tile_clicked((0, 0))
        assert consumed is False


class TestMeasureModeTwoClick:

    def test_first_click_sets_start(self, mode):
        mode.toggle()
        consumed = mode.on_tile_clicked((0, 0))
        assert consumed is True
        assert mode._start == (0, 0)

    def test_second_click_measures(self, mode, overlay, status_bar):
        mode.toggle()
        mode.on_tile_clicked((0, 0))
        consumed = mode.on_tile_clicked((3, 0))
        assert consumed is True
        # Overlay should now show a path
        assert overlay.is_visible
        # Status bar should show measurement
        status_bar.showMessage.assert_called()
        last_msg = status_bar.showMessage.call_args[0][0]
        assert "ft" in last_msg or "tiles" in last_msg

    def test_start_resets_after_measurement(self, mode):
        mode.toggle()
        mode.on_tile_clicked((0, 0))
        mode.on_tile_clicked((3, 0))
        # Start should be cleared for next measurement
        assert mode._start is None
        # Mode stays active for repeated measurements
        assert mode.active is True

    def test_same_tile_measurement(self, mode, status_bar):
        mode.toggle()
        mode.on_tile_clicked((2, 2))
        mode.on_tile_clicked((2, 2))
        last_msg = status_bar.showMessage.call_args[0][0]
        assert "0ft" in last_msg


class TestMeasureModeCancel:

    def test_cancel_clears_state(self, mode):
        mode.toggle()
        mode.on_tile_clicked((0, 0))
        mode.cancel()
        assert mode._start is None
        assert mode.active is False

    def test_cancel_clears_overlay(self, mode, overlay):
        mode.toggle()
        mode.on_tile_clicked((0, 0))
        mode.on_tile_clicked((3, 0))
        assert overlay.is_visible
        mode.cancel()
        assert not overlay.is_visible

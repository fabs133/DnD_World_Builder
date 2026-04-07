"""Tests for portrait_resolver — no Qt needed."""

import pytest
from unittest.mock import MagicMock
from ui.animations.portrait_resolver import health_state, resolve_portrait


class TestHealthState:
    def test_full_hp(self):
        assert health_state(1.0) == "healthy"

    def test_76_percent(self):
        assert health_state(0.76) == "healthy"

    def test_75_percent(self):
        assert health_state(0.75) == "wounded"

    def test_51_percent(self):
        assert health_state(0.51) == "wounded"

    def test_50_percent(self):
        assert health_state(0.50) == "bloodied"

    def test_26_percent(self):
        assert health_state(0.26) == "bloodied"

    def test_25_percent(self):
        assert health_state(0.25) == "critical"

    def test_zero(self):
        assert health_state(0.0) == "critical"


class TestResolvePortrait:
    def test_no_image_returns_none(self):
        entity = MagicMock(hp_percent=1.0, portraits={}, image_path=None)
        assert resolve_portrait(entity) is None

    def test_image_path_fallback(self):
        entity = MagicMock(hp_percent=0.3, portraits={}, image_path="goblin.png")
        assert resolve_portrait(entity) == "goblin.png"

    def test_portraits_dict_exact_match(self):
        entity = MagicMock(
            hp_percent=0.4,
            portraits={"bloodied": "goblin_blood.png", "healthy": "goblin.png"},
            image_path="goblin.png",
        )
        assert resolve_portrait(entity) == "goblin_blood.png"

    def test_portraits_fallback_to_higher(self):
        entity = MagicMock(
            hp_percent=0.1,
            portraits={"healthy": "goblin.png"},
            image_path=None,
        )
        assert resolve_portrait(entity) == "goblin.png"

    def test_base_dir_resolution(self):
        entity = MagicMock(hp_percent=1.0, portraits={}, image_path="goblin.png")
        result = resolve_portrait(entity, base_dir="/game/assets")
        assert result.replace("\\", "/") == "/game/assets/goblin.png"

    def test_absolute_path_not_resolved(self):
        import os
        abs_path = os.path.abspath("/abs/goblin.png")
        entity = MagicMock(hp_percent=1.0, portraits={}, image_path=abs_path)
        result = resolve_portrait(entity, base_dir="/other")
        assert result == abs_path

    def test_no_portraits_attr(self):
        """Entity without portraits attribute uses image_path."""
        entity = MagicMock(spec=[])
        entity.hp_percent = 1.0
        entity.image_path = "fallback.png"
        del entity.portraits
        assert resolve_portrait(entity) == "fallback.png"

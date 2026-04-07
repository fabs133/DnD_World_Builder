"""Tests for extended theme palettes (TOME, STONE, accessors)."""

import re
from core import theme_palette as tp
from core.theme_palette import TOME, STONE


_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")
_BG_KEYS = ("bg_primary", "bg_secondary", "bg_tertiary", "bg_input",
            "bg_hover", "bg_pressed", "bg_selected", "bg_disabled")
_TEXT_KEYS = ("text_primary", "text_secondary", "text_tertiary", "text_disabled")
_ACCENT_KEYS = ("accent_primary", "accent_secondary", "accent_info",
                "accent_success", "accent_warning", "accent_danger")
_BORDER_KEYS = ("border_primary", "border_secondary", "border_tertiary", "border_focus")


class TestTomePalette:
    def test_has_all_bg_keys(self):
        for k in _BG_KEYS:
            assert k in TOME, f"TOME missing {k}"

    def test_has_all_text_keys(self):
        for k in _TEXT_KEYS:
            assert k in TOME, f"TOME missing {k}"

    def test_has_all_accent_keys(self):
        for k in _ACCENT_KEYS:
            assert k in TOME, f"TOME missing {k}"

    def test_has_all_border_keys(self):
        for k in _BORDER_KEYS:
            assert k in TOME, f"TOME missing {k}"

    def test_has_stat_block_keys(self):
        for k in ("stat_bg", "stat_text", "stat_header", "stat_border"):
            assert k in TOME

    def test_has_font_family(self):
        assert "font_family" in TOME
        assert "font_family_mono" in TOME


class TestStonePalette:
    def test_has_all_bg_keys(self):
        for k in _BG_KEYS:
            assert k in STONE, f"STONE missing {k}"

    def test_has_all_text_keys(self):
        for k in _TEXT_KEYS:
            assert k in STONE, f"STONE missing {k}"

    def test_has_all_accent_keys(self):
        for k in _ACCENT_KEYS:
            assert k in STONE, f"STONE missing {k}"

    def test_has_all_border_keys(self):
        for k in _BORDER_KEYS:
            assert k in STONE, f"STONE missing {k}"

    def test_has_stat_block_keys(self):
        for k in ("stat_bg", "stat_text", "stat_header", "stat_border"):
            assert k in STONE

    def test_has_hp_colors(self):
        for k in ("hp_healthy", "hp_wounded", "hp_bloodied", "hp_critical"):
            assert k in STONE

    def test_has_font_family(self):
        assert "font_family" in STONE
        assert "font_family_mono" in STONE


class TestAllColorsValid:
    def test_tome_hex(self):
        for key, val in TOME.items():
            if key.startswith("font_"):
                continue
            assert _HEX_RE.match(val), f"TOME['{key}'] = '{val}' is not valid hex"

    def test_stone_hex(self):
        for key, val in STONE.items():
            if key.startswith("font_"):
                continue
            assert _HEX_RE.match(val), f"STONE['{key}'] = '{val}' is not valid hex"


class TestActiveTheme:
    def test_set_and_get(self):
        tp.set_active_theme("stone")
        assert tp.get_active_theme() == "stone"
        tp.set_active_theme("tome")
        assert tp.get_active_theme() == "tome"

    def test_palette_returns_active(self):
        tp.set_active_theme("tome")
        assert tp.palette() is TOME
        tp.set_active_theme("stone")
        assert tp.palette() is STONE
        tp.set_active_theme("tome")  # reset


class TestGetThemed:
    def test_explicit_tome(self):
        assert tp.get_themed("bg_primary", "tome") == TOME["bg_primary"]

    def test_explicit_stone(self):
        assert tp.get_themed("bg_primary", "stone") == STONE["bg_primary"]

    def test_uses_active(self):
        tp.set_active_theme("stone")
        assert tp.get_themed("bg_primary") == STONE["bg_primary"]
        tp.set_active_theme("tome")
        assert tp.get_themed("bg_primary") == TOME["bg_primary"]

    def test_missing_key_returns_white(self):
        assert tp.get_themed("nonexistent_xyz") == "#ffffff"


class TestGetBackwardCompat:
    def test_stat_bg_works(self):
        tp.set_active_theme("tome")
        result = tp.get("stat_bg")
        assert _HEX_RE.match(result)
        assert result == TOME["stat_bg"]

    def test_stone_stat_bg(self):
        tp.set_active_theme("stone")
        result = tp.get("stat_bg")
        assert result == STONE["stat_bg"]
        tp.set_active_theme("tome")  # reset

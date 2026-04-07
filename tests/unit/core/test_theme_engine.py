"""Tests for ThemeEngine QSS generation."""

import pytest
from unittest.mock import MagicMock
from core.theme_engine import ThemeEngine, ThemeMode
from core.theme_palette import TOME, STONE
from core import theme_palette as tp


@pytest.fixture
def engine():
    return ThemeEngine()


class TestGenerateQSS:

    def test_tome_not_empty(self, engine):
        qss = engine.generate_qss(ThemeMode.TOME)
        assert len(qss) > 500

    def test_stone_not_empty(self, engine):
        qss = engine.generate_qss(ThemeMode.STONE)
        assert len(qss) > 500

    def test_tome_contains_all_widget_types(self, engine):
        qss = engine.generate_qss(ThemeMode.TOME)
        for w in ("QPushButton", "QLineEdit", "QComboBox", "QLabel",
                   "QDockWidget", "QProgressBar", "QTabBar", "QMenu",
                   "QScrollBar", "QCheckBox", "QSlider", "QToolTip",
                   "QListWidget", "QStatusBar", "QToolButton", "QRadioButton",
                   "QTextBrowser", "QDialog", "QFrame"):
            assert w in qss, f"Missing {w}"

    def test_stone_contains_all_widget_types(self, engine):
        qss = engine.generate_qss(ThemeMode.STONE)
        for w in ("QPushButton", "QLineEdit", "QComboBox", "QCheckBox",
                   "QProgressBar", "QScrollBar", "QMenu"):
            assert w in qss, f"Missing {w}"

    def test_tome_uses_tome_colors(self, engine):
        qss = engine.generate_qss(ThemeMode.TOME)
        assert TOME["bg_primary"] in qss
        assert TOME["text_primary"] in qss

    def test_stone_uses_stone_colors(self, engine):
        qss = engine.generate_qss(ThemeMode.STONE)
        assert STONE["bg_primary"] in qss
        assert STONE["text_primary"] in qss

    def test_tome_no_stone_bg(self, engine):
        qss = engine.generate_qss(ThemeMode.TOME)
        assert STONE["bg_primary"] not in qss

    def test_tome_has_serif_font(self, engine):
        qss = engine.generate_qss(ThemeMode.TOME)
        assert "Palatino" in qss or "Georgia" in qss

    def test_stone_has_sans_font(self, engine):
        qss = engine.generate_qss(ThemeMode.STONE)
        assert "Segoe UI" in qss or "Noto Sans" in qss

    def test_tome_has_5px_radius(self, engine):
        qss = engine.generate_qss(ThemeMode.TOME)
        assert "border-radius: 5px" in qss

    def test_stone_has_3px_radius(self, engine):
        qss = engine.generate_qss(ThemeMode.STONE)
        assert "border-radius: 3px" in qss


class TestApplyAndSwap:

    def test_apply_sets_stylesheet(self, engine, qapp):
        engine.apply(qapp, ThemeMode.TOME)
        assert len(qapp.styleSheet()) > 500

    def test_apply_sets_active_mode(self, engine, qapp):
        engine.apply(qapp, ThemeMode.STONE)
        assert engine.get_active_mode() == ThemeMode.STONE

    def test_apply_sets_palette(self, engine, qapp):
        engine.apply(qapp, ThemeMode.STONE)
        assert tp.get("bg_primary") == STONE["bg_primary"]
        engine.apply(qapp, ThemeMode.TOME)  # reset

    def test_apply_persists_to_settings(self, qapp):
        settings = MagicMock()
        eng = ThemeEngine(settings_manager=settings)
        eng.apply(qapp, ThemeMode.STONE)
        settings.set.assert_called_with("ui_theme", "stone")

    def test_swap_changes_stylesheet(self, engine, qapp):
        engine.apply(qapp, ThemeMode.TOME)
        tome_qss = qapp.styleSheet()
        engine.swap_to(ThemeMode.STONE)
        stone_qss = qapp.styleSheet()
        assert tome_qss != stone_qss

    def test_swap_updates_mode(self, engine, qapp):
        engine.apply(qapp, ThemeMode.TOME)
        engine.swap_to(ThemeMode.STONE)
        assert engine.get_active_mode() == ThemeMode.STONE

    def test_default_mode_is_tome(self, engine):
        assert engine.get_active_mode() == ThemeMode.TOME


class TestThemeRoleSelectors:
    """Verify themeRole QSS selectors are generated."""

    def test_primary_button(self, engine):
        qss = engine.generate_qss(ThemeMode.TOME)
        assert 'themeRole="primary"' in qss

    def test_section_title_with_cinzel(self, engine):
        qss = engine.generate_qss(ThemeMode.TOME)
        assert 'themeRole="section-title"' in qss
        assert "Cinzel" in qss

    def test_ghost_button(self, engine):
        qss = engine.generate_qss(ThemeMode.STONE)
        assert 'themeRole="ghost"' in qss

    def test_hint_label(self, engine):
        qss = engine.generate_qss(ThemeMode.TOME)
        assert 'themeRole="hint"' in qss

    def test_card_frame(self, engine):
        qss = engine.generate_qss(ThemeMode.TOME)
        assert 'themeRole="card"' in qss

    def test_panel_header(self, engine):
        qss = engine.generate_qss(ThemeMode.STONE)
        assert 'themeRole="panel-header"' in qss

    def test_status_active(self, engine):
        qss = engine.generate_qss(ThemeMode.TOME)
        assert 'themeRole="status-active"' in qss


class TestBuildPalette:
    """Verify QPalette construction."""

    def test_returns_qpalette(self, engine):
        from PyQt5.QtGui import QPalette
        pal = engine._build_palette(ThemeMode.TOME)
        assert isinstance(pal, QPalette)

    def test_tome_window_color(self, engine):
        from PyQt5.QtGui import QPalette, QColor
        pal = engine._build_palette(ThemeMode.TOME)
        assert pal.color(QPalette.Window) == QColor(TOME["bg_primary"])

    def test_stone_window_color(self, engine):
        from PyQt5.QtGui import QPalette, QColor
        pal = engine._build_palette(ThemeMode.STONE)
        assert pal.color(QPalette.Window) == QColor(STONE["bg_primary"])


class TestThemeChangedSignal:
    """Verify ThemeEngine emits theme_changed signal."""

    def test_signal_exists(self, engine):
        assert hasattr(engine, 'theme_changed')

    def test_swap_emits_signal(self, engine, qapp):
        emitted = []
        engine.theme_changed.connect(lambda name: emitted.append(name))
        engine.swap_to(ThemeMode.STONE)
        assert emitted == ["stone"]
        engine.swap_to(ThemeMode.TOME)  # reset

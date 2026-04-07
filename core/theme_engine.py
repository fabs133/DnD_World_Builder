"""Custom QSS theme engine replacing qt-material.

Generates complete Qt Style Sheets from TOME and STONE palettes.
Supports runtime theme switching without restart.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal

from core.theme_palette import TOME, STONE


class ThemeMode(Enum):
    TOME = "tome"
    STONE = "stone"


class ThemeEngine(QObject):
    """Generates and applies Qt Style Sheets from theme palettes.

    Emits :pyqtSignal:`theme_changed` with the mode name ("tome"/"stone")
    whenever the active theme is swapped at runtime.

    :param settings_manager: Optional SettingsManager for persisting theme choice.
    """

    theme_changed = pyqtSignal(str)

    def __init__(self, settings_manager: Any = None, parent: QObject | None = None):
        super().__init__(parent)
        self._settings = settings_manager
        self._active_mode: ThemeMode = ThemeMode.TOME
        self._qss_cache: dict[ThemeMode, str] = {}

    def get_active_mode(self) -> ThemeMode:
        return self._active_mode

    def generate_qss(self, mode: ThemeMode) -> str:
        """Generate a complete QSS string for the given theme mode."""
        p = TOME if mode == ThemeMode.TOME else STONE
        r = "5px" if mode == ThemeMode.TOME else "3px"
        rs = "3px" if mode == ThemeMode.TOME else "2px"

        return f"""
/* ── Global ────────────────────────────────────────────── */
QWidget {{
    background-color: {p["bg_primary"]};
    color: {p["text_primary"]};
    font-family: {p["font_family"]};
    font-size: 13px;
}}

/* ── Buttons ───────────────────────────────────────────── */
QPushButton {{
    background-color: {p["bg_tertiary"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border_secondary"]};
    border-radius: {r};
    padding: 6px 16px;
    min-height: 24px;
}}
QPushButton:hover {{
    background-color: {p["bg_hover"]};
    border-color: {p["border_primary"]};
}}
QPushButton:pressed {{
    background-color: {p["bg_pressed"]};
}}
QPushButton:disabled {{
    background-color: {p["bg_disabled"]};
    color: {p["text_disabled"]};
    border-color: {p["border_tertiary"]};
}}
QPushButton:checked {{
    background-color: {p["accent_primary"]};
    color: {p["bg_primary"]};
    border-color: {p["accent_primary"]};
}}

QToolButton {{
    background-color: {p["bg_tertiary"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border_secondary"]};
    border-radius: {rs};
    padding: 4px 10px;
}}
QToolButton:hover {{
    background-color: {p["bg_hover"]};
    border-color: {p["border_primary"]};
}}
QToolButton:pressed {{
    background-color: {p["bg_pressed"]};
}}
QToolButton:checked {{
    background-color: {p["accent_primary"]};
    color: {p["bg_primary"]};
    border-color: {p["accent_primary"]};
}}

/* ── Labels ────────────────────────────────────────────── */
QLabel {{
    background-color: transparent;
    border: none;
    padding: 0px;
}}
QLabel:disabled {{
    color: {p["text_disabled"]};
}}

/* ── Text Inputs ───────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {p["bg_input"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border_secondary"]};
    border-radius: {rs};
    padding: 4px 8px;
    selection-background-color: {p["accent_primary"]};
    selection-color: {p["bg_primary"]};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {p["border_focus"]};
}}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background-color: {p["bg_disabled"]};
    color: {p["text_disabled"]};
}}
QLineEdit:read-only {{
    background-color: {p["bg_secondary"]};
}}

/* ── ComboBox ──────────────────────────────────────────── */
QComboBox {{
    background-color: {p["bg_input"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border_secondary"]};
    border-radius: {rs};
    padding: 4px 8px;
    min-height: 24px;
}}
QComboBox:hover {{
    border-color: {p["border_primary"]};
}}
QComboBox:focus {{
    border-color: {p["border_focus"]};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {p["bg_secondary"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border_secondary"]};
    selection-background-color: {p["bg_selected"]};
    selection-color: {p["text_primary"]};
}}

/* ── SpinBox ───────────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {{
    background-color: {p["bg_input"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border_secondary"]};
    border-radius: {rs};
    padding: 4px 8px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {p["border_focus"]};
}}

/* ── CheckBox + RadioButton ────────────────────────────── */
QCheckBox {{
    spacing: 8px;
    color: {p["text_primary"]};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {p["border_secondary"]};
    border-radius: 3px;
    background: transparent;
}}
QCheckBox::indicator:checked {{
    background-color: {p["accent_primary"]};
    border-color: {p["accent_primary"]};
}}
QCheckBox::indicator:disabled {{
    border-color: {p["border_tertiary"]};
    background-color: {p["bg_disabled"]};
}}
QRadioButton {{
    spacing: 8px;
    color: {p["text_primary"]};
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {p["border_secondary"]};
    border-radius: 8px;
    background: transparent;
}}
QRadioButton::indicator:checked {{
    background-color: {p["accent_primary"]};
    border-color: {p["accent_primary"]};
}}

/* ── ProgressBar ───────────────────────────────────────── */
QProgressBar {{
    background-color: {p["progress_bg"]};
    border: 1px solid {p["border_tertiary"]};
    border-radius: {rs};
    text-align: center;
    color: {p["text_secondary"]};
    min-height: 16px;
}}
QProgressBar::chunk {{
    background-color: {p["progress_fill"]};
    border-radius: {rs};
}}

/* ── Slider ────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 6px;
    background: {p["progress_bg"]};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    width: 16px;
    height: 16px;
    margin: -5px 0;
    background: {p["accent_primary"]};
    border-radius: 8px;
}}

/* ── Tabs ──────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {p["border_secondary"]};
    background-color: {p["bg_primary"]};
}}
QTabBar::tab {{
    background-color: {p["bg_tertiary"]};
    color: {p["text_secondary"]};
    border: 1px solid {p["border_secondary"]};
    border-bottom: none;
    padding: 6px 16px;
    margin-right: 2px;
    border-top-left-radius: {rs};
    border-top-right-radius: {rs};
}}
QTabBar::tab:selected {{
    background-color: {p["bg_primary"]};
    color: {p["accent_primary"]};
    border-bottom: 2px solid {p["accent_primary"]};
}}
QTabBar::tab:hover:!selected {{
    background-color: {p["bg_hover"]};
}}

/* ── DockWidget ────────────────────────────────────────── */
QDockWidget {{
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}}
QDockWidget::title {{
    background-color: {p["bg_secondary"]};
    color: {p["text_primary"]};
    padding: 6px 10px;
    border-bottom: 1px solid {p["border_secondary"]};
}}

/* ── MenuBar + Menu ────────────────────────────────────── */
QMenuBar {{
    background-color: {p["bg_secondary"]};
    color: {p["text_primary"]};
    border-bottom: 1px solid {p["border_tertiary"]};
}}
QMenuBar::item {{
    padding: 4px 12px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background-color: {p["bg_hover"]};
}}
QMenu {{
    background-color: {p["bg_secondary"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border_secondary"]};
}}
QMenu::item {{
    padding: 6px 24px;
}}
QMenu::item:selected {{
    background-color: {p["bg_selected"]};
}}
QMenu::separator {{
    height: 1px;
    background: {p["border_tertiary"]};
    margin: 4px 8px;
}}

/* ── Toolbar + StatusBar ───────────────────────────────── */
QToolBar {{
    background-color: {p["bg_secondary"]};
    border-bottom: 1px solid {p["border_tertiary"]};
    spacing: 4px;
    padding: 2px;
}}
QStatusBar {{
    background-color: {p["bg_secondary"]};
    color: {p["text_secondary"]};
    border-top: 1px solid {p["border_tertiary"]};
}}

/* ── ScrollBar ─────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {p["scrollbar_bg"]};
    width: 12px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {p["scrollbar_handle"]};
    border-radius: 4px;
    min-height: 30px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: {p["scrollbar_hover"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: {p["scrollbar_bg"]};
    height: 12px;
}}
QScrollBar::handle:horizontal {{
    background: {p["scrollbar_handle"]};
    border-radius: 4px;
    min-width: 30px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {p["scrollbar_hover"]};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ── Splitter ──────────────────────────────────────────── */
QSplitter::handle {{
    background: {p["border_tertiary"]};
}}
QSplitter::handle:horizontal {{
    width: 3px;
}}
QSplitter::handle:vertical {{
    height: 3px;
}}

/* ── GroupBox ──────────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {p["border_tertiary"]};
    border-radius: {r};
    margin-top: 8px;
    padding-top: 16px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    padding: 0 6px;
    color: {p["accent_primary"]};
}}

/* ── List/Tree/Table ───────────────────────────────────── */
QListWidget, QTreeWidget, QTableWidget {{
    background-color: {p["bg_input"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border_secondary"]};
    border-radius: {rs};
}}
QListWidget::item, QTreeWidget::item {{
    padding: 4px 8px;
}}
QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: {p["bg_selected"]};
    color: {p["text_primary"]};
}}
QListWidget::item:hover, QTreeWidget::item:hover {{
    background-color: {p["bg_hover"]};
}}
QHeaderView::section {{
    background-color: {p["bg_secondary"]};
    color: {p["text_secondary"]};
    border: 1px solid {p["border_tertiary"]};
    padding: 4px 8px;
}}

/* ── ToolTip ───────────────────────────────────────────── */
QToolTip {{
    background-color: {p["bg_secondary"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border_secondary"]};
    padding: 4px 8px;
    border-radius: {rs};
}}

/* ── TextBrowser ───────────────────────────────────────── */
QTextBrowser {{
    background-color: {p["stat_bg"]};
    border: none;
}}

/* ── Dialog ────────────────────────────────────────────── */
QDialog {{
    background-color: {p["bg_primary"]};
}}

/* ── ScrollArea ────────────────────────────────────────── */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

/* ── Frame ─────────────────────────────────────────────── */
QFrame {{
    border: none;
}}

/* ── Semantic themeRole selectors ──────────────────────── */
QPushButton[themeRole="primary"] {{
    background-color: {p["accent_success"]};
    color: {p["bg_primary"]};
    font-weight: bold;
    border: 1px solid {p["accent_success"]};
    padding: 10px 20px;
    font-size: 14px;
    border-radius: {r};
}}
QPushButton[themeRole="primary"]:hover {{
    background-color: {p["accent_primary"]};
    border-color: {p["accent_primary"]};
}}
QPushButton[themeRole="primary"]:pressed {{
    background-color: {p["bg_pressed"]};
}}

QPushButton[themeRole="danger"] {{
    background-color: {p["accent_danger"]};
    color: {p["bg_primary"]};
    border: 1px solid {p["accent_danger"]};
    font-weight: bold;
    border-radius: {r};
}}
QPushButton[themeRole="danger"]:hover {{
    background-color: {p["accent_warning"]};
}}

QPushButton[themeRole="ghost"] {{
    background: transparent;
    border: 1px solid {p["border_tertiary"]};
    color: {p["text_secondary"]};
    border-radius: {rs};
    text-align: left;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}}
QPushButton[themeRole="ghost"]:hover {{
    background-color: {p["bg_hover"]};
    border-color: {p["border_secondary"]};
    color: {p["text_primary"]};
}}

QToolButton[themeRole="tab-active"] {{
    background-color: {p["bg_primary"]};
    color: {p["accent_primary"]};
    border: 1px solid {p["border_secondary"]};
    border-bottom: 2px solid {p["accent_primary"]};
    font-weight: bold;
}}

QLabel[themeRole="section-title"] {{
    font-family: 'Cinzel', 'Palatino Linotype', serif;
    font-size: 15px;
    color: {p["accent_primary"]};
    padding: 4px 0px;
    background: transparent;
}}

QLabel[themeRole="panel-header"] {{
    font-family: 'Cinzel', 'Palatino Linotype', serif;
    font-size: 18px;
    font-weight: bold;
    color: {p["accent_primary"]};
    padding: 8px 0px;
    background: transparent;
}}

QLabel[themeRole="hint"] {{
    color: {p["text_tertiary"]};
    font-size: 11px;
    font-style: italic;
    background: transparent;
}}

QLabel[themeRole="status-active"] {{
    color: {p["accent_success"]};
    font-weight: bold;
    border: 1px solid {p["accent_success"]};
    border-radius: {rs};
    padding: 2px 8px;
    background: transparent;
}}

QFrame[themeRole="inset-panel"] {{
    background-color: {p["bg_secondary"]};
    border: 1px solid {p["border_tertiary"]};
    border-radius: {r};
}}

QFrame[themeRole="card"] {{
    background-color: {p["bg_secondary"]};
    border: 1px solid {p["border_secondary"]};
    border-radius: {r};
    padding: 12px;
}}
"""

    # ── QPalette sync ─────────────────────────────────────────────────

    @staticmethod
    def _build_palette(mode: ThemeMode):
        """Build a QPalette matching the active theme dict."""
        from PyQt5.QtGui import QPalette, QColor
        p = TOME if mode == ThemeMode.TOME else STONE
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(p["bg_primary"]))
        pal.setColor(QPalette.WindowText, QColor(p["text_primary"]))
        pal.setColor(QPalette.Base, QColor(p["bg_input"]))
        pal.setColor(QPalette.AlternateBase, QColor(p["bg_secondary"]))
        pal.setColor(QPalette.Text, QColor(p["text_primary"]))
        pal.setColor(QPalette.Button, QColor(p["bg_tertiary"]))
        pal.setColor(QPalette.ButtonText, QColor(p["text_primary"]))
        pal.setColor(QPalette.Highlight, QColor(p["accent_primary"]))
        pal.setColor(QPalette.HighlightedText, QColor(p["bg_primary"]))
        pal.setColor(QPalette.ToolTipBase, QColor(p["bg_secondary"]))
        pal.setColor(QPalette.ToolTipText, QColor(p["text_primary"]))
        pal.setColor(QPalette.Link, QColor(p["accent_info"]))
        pal.setColor(QPalette.Disabled, QPalette.WindowText, QColor(p["text_disabled"]))
        pal.setColor(QPalette.Disabled, QPalette.Text, QColor(p["text_disabled"]))
        pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(p["text_disabled"]))
        return pal

    def apply(self, app: Any, mode: ThemeMode) -> None:
        """Generate QSS and apply to the QApplication."""
        from core import theme_palette as tp
        tp.set_active_theme(mode.value)
        self._active_mode = mode

        # Force Fusion style for cross-platform consistency
        if hasattr(app, 'setStyle'):
            app.setStyle("Fusion")
        if hasattr(app, 'setPalette'):
            app.setPalette(self._build_palette(mode))

        if mode not in self._qss_cache:
            self._qss_cache[mode] = self.generate_qss(mode)
        app.setStyleSheet(self._qss_cache[mode])

        if self._settings:
            self._settings.set("ui_theme", mode.value)

    def swap_to(self, mode: ThemeMode) -> None:
        """Runtime theme swap without restart. Also syncs sound theme."""
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            self._qss_cache.pop(mode, None)  # force regeneration
            self.apply(app, mode)
        # Sync sound manager theme
        try:
            from core.audio.ui_sound_manager import UISoundManager
            UISoundManager.instance().set_theme(mode.value)
        except Exception:
            pass
        self.theme_changed.emit(mode.value)

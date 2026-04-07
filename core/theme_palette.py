"""Theme color palettes for the DnD World Builder.

Provides DARK/LIGHT (legacy), TOME (exploration), and STONE (combat) palettes.
The active theme is controlled by :func:`set_active_theme` and read by
:func:`get`, :func:`get_themed`, and :func:`palette`.
"""

import logging

from PyQt5.QtWidgets import QApplication

_logger = logging.getLogger(__name__)


def _is_dark() -> bool:
    app = QApplication.instance()
    return app.palette().window().color().lightness() < 128 if app else True


# ── Legacy palettes (stat block + graph node colors) ─────────────────────

DARK = {
    "stat_bg":        "#1e1e2e",
    "stat_text":      "#e0d7c8",
    "stat_header":    "#c084fc",
    "stat_border":    "#6d4c9e",
    "stat_sep_edge":  "#c084fc",
    "stat_sep_mid":   "#2d2d5e",
    "stat_subheader": "#b0a8c8",
    "stat_lore":      "#a09898",
    "node_bg":        "#2d2d5e",
    "node_border":    "#7b7bdd",
    "node_text":      "#e0d7ff",
    "arrow":          "#f97316",
}

LIGHT = {
    "stat_bg":        "#fdf1dc",
    "stat_text":      "#1a1a1a",
    "stat_header":    "#7a200d",
    "stat_border":    "#7a200d",
    "stat_sep_edge":  "#7a200d",
    "stat_sep_mid":   "#e0c8a8",
    "stat_subheader": "#333333",
    "stat_lore":      "#444444",
    "node_bg":        "#ccccff",
    "node_border":    "#000000",
    "node_text":      "#000000",
    "arrow":          "#cc0000",
}


# ── Tome palette — warm parchment, exploration ───────────────────────────

TOME = {
    # Backgrounds
    "bg_primary":       "#f0e6cc",
    "bg_secondary":     "#faf4e4",
    "bg_tertiary":      "#ede2c6",
    "bg_input":         "#fdf8ee",
    "bg_hover":         "#e8dab5",
    "bg_pressed":       "#ddd0a8",
    "bg_selected":      "#e0d4b4",
    "bg_disabled":      "#e8e0cc",
    # Text
    "text_primary":     "#3d2e1a",
    "text_secondary":   "#6b5a3e",
    "text_tertiary":    "#8a7050",
    "text_disabled":    "#b0a080",
    # Accents
    "accent_primary":   "#7a200d",
    "accent_secondary": "#8b6914",
    "accent_info":      "#2a5a8a",
    "accent_success":   "#2a6a30",
    "accent_warning":   "#8a6a10",
    "accent_danger":    "#8a2020",
    # Borders
    "border_primary":   "#b09060",
    "border_secondary": "#c4a46a",
    "border_tertiary":  "#d4be8a",
    "border_focus":     "#7a200d",
    # Scrollbar
    "scrollbar_bg":     "#ede2c6",
    "scrollbar_handle": "#c4a46a",
    "scrollbar_hover":  "#b09060",
    # Progress
    "progress_bg":      "#d4be8a",
    "progress_fill":    "#7a200d",
    # Fonts
    "font_family":      "'Palatino Linotype', 'Book Antiqua', Palatino, 'Georgia', serif",
    "font_family_mono": "'Consolas', 'Courier New', monospace",
    # Semantic
    "enemy":            "#7a200d",
    "ally":             "#1e5a32",
    "npc":              "#6b4f0e",
    # Stat block (matches existing LIGHT)
    "stat_bg":          "#fdf1dc",
    "stat_text":        "#1a1a1a",
    "stat_header":      "#7a200d",
    "stat_border":      "#7a200d",
    "stat_sep_edge":    "#7a200d",
    "stat_sep_mid":     "#e0c8a8",
    "stat_subheader":   "#333333",
    "stat_lore":        "#444444",
    # Graph nodes
    "node_bg":          "#ccccff",
    "node_border":      "#000000",
    "node_text":        "#000000",
    "arrow":            "#cc0000",
}

# ── Stone palette — dark worn stone, combat ──────────────────────────────

STONE = {
    # Backgrounds
    "bg_primary":       "#221e19",
    "bg_secondary":     "#2a2520",
    "bg_tertiary":      "#332c24",
    "bg_input":         "#2e2820",
    "bg_hover":         "#3a3228",
    "bg_pressed":       "#1a1814",
    "bg_selected":      "#3a3228",
    "bg_disabled":      "#282420",
    # Text
    "text_primary":     "#c4b89a",
    "text_secondary":   "#8a7e6e",
    "text_tertiary":    "#6a6050",
    "text_disabled":    "#5a5448",
    # Accents
    "accent_primary":   "#e8c860",
    "accent_secondary": "#d4a040",
    "accent_info":      "#6080c0",
    "accent_success":   "#60a060",
    "accent_warning":   "#c89030",
    "accent_danger":    "#a03030",
    # Borders
    "border_primary":   "#5a4e3e",
    "border_secondary": "#4a4035",
    "border_tertiary":  "#3a3228",
    "border_focus":     "#e8c860",
    # Scrollbar
    "scrollbar_bg":     "#2a2520",
    "scrollbar_handle": "#4a4035",
    "scrollbar_hover":  "#5a4e3e",
    # Progress / HP
    "progress_bg":      "#332c24",
    "progress_fill":    "#e8c860",
    "hp_healthy":       "#3a6a2a",
    "hp_wounded":       "#7a6a20",
    "hp_bloodied":      "#8a2a2a",
    "hp_critical":      "#a02020",
    # Fonts
    "font_family":      "'Segoe UI', 'Noto Sans', 'Helvetica Neue', Arial, sans-serif",
    "font_family_mono": "'Consolas', 'Courier New', monospace",
    # Semantic
    "enemy":            "#d48080",
    "enemy_bg":         "#3a1a1a",
    "ally":             "#80c880",
    "ally_bg":          "#1a2a1a",
    # Stat block (stone variant)
    "stat_bg":          "#2a2520",
    "stat_text":        "#c4b89a",
    "stat_header":      "#e8c860",
    "stat_border":      "#4a4035",
    "stat_sep_edge":    "#5a4e3e",
    "stat_sep_mid":     "#332c24",
    "stat_subheader":   "#8a7e6e",
    "stat_lore":        "#6a6050",
    # Graph nodes
    "node_bg":          "#2d2d5e",
    "node_border":      "#7b7bdd",
    "node_text":        "#e0d7ff",
    "arrow":            "#f97316",
}


# ── Active theme state ───────────────────────────────────────────────────

_active_theme = "tome"


def set_active_theme(theme: str) -> None:
    """Set the active theme palette. Called by ThemeEngine."""
    global _active_theme
    _active_theme = theme


def get_active_theme() -> str:
    """Return the currently active theme name."""
    return _active_theme


def palette() -> dict:
    """Return the full active palette dict."""
    return TOME if _active_theme == "tome" else STONE


# ── Accessors ────────────────────────────────────────────────────────────

def get(key: str) -> str:
    """Get a color from the active palette, falling back to legacy DARK/LIGHT.

    Backward compatible with existing code using stat_bg, stat_text, etc.
    """
    p = TOME if _active_theme == "tome" else STONE
    val = p.get(key)
    if val is not None:
        return val
    fallback = (DARK if _is_dark() else LIGHT).get(key)
    if fallback is not None:
        return fallback
    _logger.warning(f"Unknown theme key: {key!r} — returning #ffffff")
    return "#ffffff"


def get_themed(key: str, theme: str = "") -> str:
    """Get a color by key from a specific or active palette.

    :param key: Color key name.
    :param theme: ``"tome"``, ``"stone"``, or ``""`` (use active theme).
    :returns: Hex color string.
    """
    if theme == "tome":
        return TOME.get(key, "#ffffff")
    if theme == "stone":
        return STONE.get(key, "#ffffff")
    p = TOME if _active_theme == "tome" else STONE
    return p.get(key, "#ffffff")

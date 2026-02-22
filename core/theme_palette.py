from PyQt5.QtWidgets import QApplication


def _is_dark() -> bool:
    app = QApplication.instance()
    return app.palette().window().color().lightness() < 128 if app else True


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


def get(key: str) -> str:
    return (DARK if _is_dark() else LIGHT).get(key, "#ffffff")

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QStackedWidget, QToolButton, QButtonGroup,
)
from PyQt5.QtCore import Qt

from ui.panels.core_values_panel import CoreValuesPanel
from ui.panels.entities_panel import EntitiesPanel
from ui.panels.trigger_panel import TriggerPanel
from ui.panels.color_mode_dialog import ColorModeDialog
from ui.panels.template_browser_panel import TemplateBrowserPanel


class TileSidePanel(QWidget):
    """
    Right-side panel shown when a tile is selected.

    Contains:
    - Header label (tile position + label)
    - Icon action bar: Core Values | Entities | Triggers | Color
    - QStackedWidget: placeholder / CoreValuesPanel / EntitiesPanel / TriggerPanel
    """

    _STACK_PLACEHOLDER = 0
    _STACK_CORE = 1
    _STACK_ENTITIES = 2
    _STACK_TRIGGERS = 3
    _STACK_TEMPLATES = 4

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main_window = main_window
        self._tile_data = None
        self._tile_item = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # --- Header ---
        self.header_label = QLabel("No tile selected")
        self.header_label.setStyleSheet("font-size: 12px; color: gray;")
        self.header_label.setWordWrap(True)
        layout.addWidget(self.header_label)

        # --- Icon action bar ---
        icon_bar = QHBoxLayout()
        icon_bar.setSpacing(4)

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        self._core_btn = self._make_view_btn("Core Values", 1)
        self._entities_btn = self._make_view_btn("Entities", 2)
        self._triggers_btn = self._make_view_btn("Triggers", 3)
        self._templates_btn = self._make_view_btn("Templates", 4)

        for btn in (self._core_btn, self._entities_btn, self._triggers_btn, self._templates_btn):
            icon_bar.addWidget(btn)

        self._color_btn = QToolButton()
        self._color_btn.setText("Color")
        self._color_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self._color_btn.setMinimumWidth(60)
        self._color_btn.clicked.connect(self._on_color_clicked)
        icon_bar.addWidget(self._color_btn)

        layout.addLayout(icon_bar)

        # --- Stacked widget ---
        self.stack = QStackedWidget()

        placeholder = QLabel("Select a tile, then choose an action above.")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: gray; font-style: italic;")
        self.stack.addWidget(placeholder)           # 0

        self.core_panel = CoreValuesPanel()
        self.stack.addWidget(self.core_panel)       # 1

        self.entities_panel = EntitiesPanel(main_window)
        self.stack.addWidget(self.entities_panel)   # 2

        self.trigger_panel = TriggerPanel()
        self.stack.addWidget(self.trigger_panel)    # 3

        self.template_panel = TemplateBrowserPanel()
        self.stack.addWidget(self.template_panel)   # 4

        layout.addWidget(self.stack)

        # Wire view buttons
        self._core_btn.clicked.connect(lambda: self._switch_to(self._STACK_CORE))
        self._entities_btn.clicked.connect(lambda: self._switch_to(self._STACK_ENTITIES))
        self._triggers_btn.clicked.connect(lambda: self._switch_to(self._STACK_TRIGGERS))
        self._templates_btn.clicked.connect(lambda: self._switch_to(self._STACK_TEMPLATES))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_tile(self, tile_data, tile_item, main_window):
        """Called by main_window.select_tile() to attach a tile to the panel."""
        self._tile_data = tile_data
        self._tile_item = tile_item
        self._main_window = main_window

        pos = tile_data.position
        label = tile_data.user_label or ""
        suffix = f" — {label}" if label else ""
        self.header_label.setText(f"Tile ({pos[0]}, {pos[1]}){suffix}")
        self.header_label.setStyleSheet("font-size: 12px; font-weight: bold;")

        # Reload the currently active view with the new tile
        self._reload_active_view()

    def open_trigger_panel_for_entity(self, entity):
        """Switch the stack to TriggerPanel and load the given entity's triggers."""
        self._triggers_btn.setChecked(True)
        self.stack.setCurrentIndex(self._STACK_TRIGGERS)
        self.trigger_panel.load(entity, entity.name)

    def update_color_btn_style(self):
        """Reflect the current color mode state on the Color button."""
        if self._main_window.color_mode_active:
            self._color_btn.setStyleSheet(
                "border: 2px solid #22c55e; border-radius: 4px; color: #22c55e;"
            )
        else:
            self._color_btn.setStyleSheet("")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _make_view_btn(self, text: str, stack_index: int) -> QToolButton:
        btn = QToolButton()
        btn.setText(text)
        btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        btn.setCheckable(True)
        btn.setMinimumWidth(70)
        self._btn_group.addButton(btn, stack_index)
        return btn

    def _switch_to(self, index: int):
        if self._tile_data is None:
            return
        self.stack.setCurrentIndex(index)
        self._reload_active_view()

    def _reload_active_view(self):
        if self._tile_data is None:
            return
        idx = self.stack.currentIndex()
        if idx == self._STACK_CORE:
            self.core_panel.load(self._tile_data, self._tile_item, self._main_window)
        elif idx == self._STACK_ENTITIES:
            self.entities_panel.load(self._tile_data, self._main_window, self)
        elif idx == self._STACK_TRIGGERS:
            pos = self._tile_data.position
            name = self._tile_data.user_label or f"Tile {pos}"
            self.trigger_panel.load(self._tile_data, name)

    def _on_color_clicked(self):
        mw = self._main_window
        dlg = ColorModeDialog(
            current_color=mw.active_color,
            color_mode_active=mw.color_mode_active,
            parent=self,
        )
        if dlg.exec_():
            mw.active_color = dlg.color
            if dlg.color_mode:
                mw.activate_color_mode(dlg.color)
            else:
                mw.deactivate_color_mode()
            self.update_color_btn_style()

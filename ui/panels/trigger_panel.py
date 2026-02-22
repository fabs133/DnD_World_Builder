from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QLineEdit, QSplitter,
)
from PyQt5.QtCore import Qt
from ui.dialogs.trigger_editor.graph_view import TriggerGraphView
from ui.dialogs.trigger_editor.property_editor import TriggerPropertyEditor
from core.logger import app_logger


class TriggerPanel(QWidget):
    """
    Embedded panel for viewing and editing triggers on a tile or entity.

    Layout:
    - Header label: "Triggers — <context name>"
    - Vertical QSplitter:
      - Top (~80%): TriggerGraphView (existing, reused)
      - Bottom (~20%): filter bar + trigger list (left) | property editor (right)

    Call :meth:`load` to attach to a tile or entity context.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._context = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # --- Header ---
        self.context_label = QLabel("Triggers")
        self.context_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.context_label)

        # --- Vertical splitter: graph (top) + bottom panel ---
        self._splitter = QSplitter(Qt.Vertical)
        layout.addWidget(self._splitter)

        # TOP: graph view
        self.graph_view = TriggerGraphView()
        self._splitter.addWidget(self.graph_view)

        # BOTTOM: filter + list (left) | property editor + save (right)
        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(6)

        # Left side: filter bar + list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        filter_row = QHBoxLayout()
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter triggers...")
        self.filter_input.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.filter_input)

        self.add_btn = QPushButton("+")
        self.add_btn.setFixedWidth(30)
        self.add_btn.setToolTip("New Trigger")
        self.add_btn.clicked.connect(self._on_new_trigger)
        filter_row.addWidget(self.add_btn)
        left_layout.addLayout(filter_row)

        self.trigger_list = QListWidget()
        self.trigger_list.currentRowChanged.connect(self._on_list_selection)
        left_layout.addWidget(self.trigger_list)

        self.empty_label = QLabel("No triggers yet")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: gray; font-style: italic; padding: 8px;")
        left_layout.addWidget(self.empty_label)

        bottom_layout.addWidget(left_widget, 1)

        # Right side: property editor + save/delete buttons
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.property_editor = TriggerPropertyEditor()
        right_layout.addWidget(self.property_editor)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save Trigger")
        save_btn.clicked.connect(self._on_save_trigger)
        delete_btn = QPushButton("Delete Trigger")
        delete_btn.clicked.connect(self._on_delete_trigger)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(delete_btn)
        right_layout.addLayout(btn_row)

        bottom_layout.addWidget(right_widget, 1)

        self._splitter.addWidget(bottom)
        self._splitter.setSizes([400, 200])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, context, context_name: str):
        """
        Attach the panel to a new trigger context (tile or entity).

        :param context: Object with a ``triggers`` list attribute.
        :param context_name: Display name shown in the header.
        """
        self._context = context
        self.context_label.setText(f"Triggers — {context_name}")
        self.graph_view.set_context(context)
        self.property_editor.set_context(context)
        self.property_editor.set_trigger(None)
        self._refresh_list()
        app_logger.debug(f"[TriggerPanel] Loaded context: {context_name}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_list(self):
        self.trigger_list.clear()
        triggers = getattr(self._context, "triggers", []) if self._context else []
        has_triggers = bool(triggers)
        self.empty_label.setVisible(not has_triggers)
        self.trigger_list.setVisible(has_triggers)
        for t in triggers:
            self.trigger_list.addItem(t.label)
        self._apply_filter(self.filter_input.text())

    def _apply_filter(self, text: str):
        for i in range(self.trigger_list.count()):
            item = self.trigger_list.item(i)
            item.setHidden(bool(text) and text.lower() not in item.text().lower())

    def _on_list_selection(self, row: int):
        if self._context is None or row < 0:
            return
        triggers = getattr(self._context, "triggers", [])
        visible_items = [
            self.trigger_list.item(i)
            for i in range(self.trigger_list.count())
            if not self.trigger_list.item(i).isHidden()
        ]
        if row < len(visible_items):
            label = visible_items[row].text() if row < len(visible_items) else None
            trigger = next((t for t in triggers if t.label == label), None)
            if trigger:
                self.property_editor.set_trigger(trigger)

    def _on_new_trigger(self):
        self.property_editor.clear_inputs()
        self.property_editor.set_defaults()
        self.property_editor.set_trigger(None)
        self.trigger_list.clearSelection()

    def _on_save_trigger(self):
        self.property_editor.save_trigger()
        self.graph_view.refresh()
        self._refresh_list()

    def _on_delete_trigger(self):
        trigger = self.property_editor.trigger
        if trigger is None or self._context is None:
            return
        self._context.triggers = [
            t for t in getattr(self._context, "triggers", [])
            if t.label != trigger.label
        ]
        self.property_editor.set_trigger(None)
        self.graph_view.refresh()
        self._refresh_list()

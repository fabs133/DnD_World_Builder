from PyQt5.QtCore import QTimer, Qt, QPointF, pyqtSignal, QObject
from PyQt5.QtGui import QBrush, QPen, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsTextItem,
)
from .trigger_node import TriggerNodeItem
from core.logger import app_logger
from core import theme_palette as tp
from typing import List

COLUMN_WIDTH = 220   # horizontal spacing between columns (matches node spacing)
ROW_HEIGHT   = 120   # vertical space between rows
GRID_CROSS   = 6     # half-size of "+" grid markers in pixels


class _GraphSignals(QObject):
    node_selected = pyqtSignal(object)   # emits the Trigger that was clicked


class _GraphicsView(QGraphicsView):
    """QGraphicsView subclass that draws a subtle column-grid background and
    handles drag-to-connect mouse events."""

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        pen = QPen(QColor(120, 120, 120, 50))
        pen.setCosmetic(True)   # 1 px regardless of zoom level
        painter.setPen(pen)
        x = 0
        while x < rect.right() + COLUMN_WIDTH:
            y = -ROW_HEIGHT
            while y < rect.bottom() + ROW_HEIGHT:
                painter.drawLine(int(x) - GRID_CROSS, int(y),
                                 int(x) + GRID_CROSS, int(y))
                painter.drawLine(int(x), int(y) - GRID_CROSS,
                                 int(x), int(y) + GRID_CROSS)
                y += ROW_HEIGHT
            x += COLUMN_WIDTH

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and hasattr(self, "_graph_widget"):
            gw = self._graph_widget
            scene_pos = self.mapToScene(event.pos())
            for node in gw.node_items:
                if node.output_port_contains(scene_pos):
                    gw._drag_source = node
                    gw._drag_line = self.scene().addLine(
                        scene_pos.x(), scene_pos.y(),
                        scene_pos.x(), scene_pos.y(),
                        QPen(QColor(tp.get("arrow")), 2, Qt.DashLine),
                    )
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if hasattr(self, "_graph_widget") and self._graph_widget._drag_line:
            gw = self._graph_widget
            sp = gw._drag_source.get_output_anchor()
            ep = self.mapToScene(event.pos())
            gw._drag_line.setLine(sp.x(), sp.y(), ep.x(), ep.y())
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if hasattr(self, "_graph_widget") and self._graph_widget._drag_line:
            gw = self._graph_widget
            self.scene().removeItem(gw._drag_line)
            gw._drag_line = None
            ep = self.mapToScene(event.pos())
            for node in gw.node_items:
                if node.input_port_contains(ep) and node is not gw._drag_source:
                    gw._drag_source.trigger.next_trigger = node.trigger.label
                    gw.build_graph(gw.context)
                    break
            gw._drag_source = None
            return
        super().mouseReleaseEvent(event)


class TriggerGraphView(QWidget):
    """
    A QWidget that displays a graph of trigger nodes using QGraphicsView and QGraphicsScene.
    Nodes are laid out in chain-order columns (BFS) with timeline headers.
    Supports drag-to-connect wiring between node ports.
    """

    def __init__(self, context=None):
        super().__init__()
        self.context = context
        self.node_items: List[TriggerNodeItem] = []

        # Drag-connect state
        self._drag_line = None
        self._drag_source = None

        # Signal — emitted when a node is clicked
        self._signals = _GraphSignals()
        self.node_selected = self._signals.node_selected

        self.scene = QGraphicsScene()
        self.view = _GraphicsView(self.scene)
        self.view._graph_widget = self   # back-reference used by mouse events

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

        if self.context:
            app_logger.debug(f"TriggerGraphView initializing with context: {context.triggers}")
            self.build_graph(self.context)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_context(self, context):
        """Set a new context and rebuild the graph."""
        app_logger.debug(f"Setting context: {context.triggers}")
        self.context = context
        self.build_graph(self.context)

    def refresh(self):
        """Rebuild the graph from the current context (called after saves)."""
        if self.context:
            self.build_graph(self.context)

    # ------------------------------------------------------------------
    # Graph building
    # ------------------------------------------------------------------

    def _assign_columns(self, triggers):
        """Return {trigger.label: column_index} using BFS chain ordering."""
        label_map = {t.label: t for t in triggers}
        pointed_at = {t.next_trigger for t in triggers if t.next_trigger}
        roots = [t for t in triggers if t.label not in pointed_at]

        col = {}
        queue = [(root, 0) for root in roots]
        visited = set()
        while queue:
            trig, c = queue.pop(0)
            if trig.label in visited:
                continue
            visited.add(trig.label)
            col[trig.label] = c
            if trig.next_trigger and trig.next_trigger in label_map:
                queue.append((label_map[trig.next_trigger], c + 1))

        # Fallback for disconnected triggers
        next_col = max(col.values(), default=-1) + 1
        for t in triggers:
            if t.label not in col:
                col[t.label] = next_col
                next_col += 1
        return col

    def build_graph(self, context):
        """Build the graph layout from the context's triggers using BFS column order."""
        if not hasattr(context, "triggers"):
            return

        self.context = context
        self.node_items.clear()
        self.scene.clear()

        col_map = self._assign_columns(context.triggers)
        col_row_counter = {}
        app_logger.debug("Starting graph layout (BFS column order)...")

        for trigger in context.triggers:
            col = col_map.get(trigger.label, 0)
            row_in_col = col_row_counter.get(col, 0)
            col_row_counter[col] = row_in_col + 1

            x = col * COLUMN_WIDTH
            y = 40 + row_in_col * 120
            node_item = TriggerNodeItem(trigger, x, y)
            self.scene.addItem(node_item)
            self.node_items.append(node_item)
            app_logger.debug(f"Node '{trigger.label}' col={col} row={row_in_col} → ({x},{y})")

        max_rows = max(col_row_counter.values(), default=1)
        total_height = 40 + max_rows * 120 + 40

        # Timeline column headers and dashed dividers
        num_cols = max(col_map.values(), default=0) + 1 if col_map else 1
        for col in range(num_cols + 1):
            x = col * COLUMN_WIDTH
            dashed = QPen(QColor(100, 100, 100, 70), 1, Qt.DashLine)
            self.scene.addLine(x, -35, x, total_height, dashed)
            if col < num_cols:
                lbl = QGraphicsTextItem(f"Round {col}")
                lbl.setDefaultTextColor(QColor(tp.get("node_text")))
                lbl.setPos(x + 8, -32)
                self.scene.addItem(lbl)

        total_width = num_cols * COLUMN_WIDTH + 100
        self.scene.setSceneRect(0, -40, total_width, total_height)
        self.view.viewport().update()
        self.scene.update()
        QTimer.singleShot(0, lambda: self.manage_graph_building_and_arrows(context))

    def manage_graph_building_and_arrows(self, context):
        """Draw arrows between trigger nodes based on their next_trigger connections."""
        app_logger.debug("Starting graph building and arrow drawing process.")
        node_map = {node.trigger.label: node for node in self.node_items}

        for trig in context.triggers:
            src_label = trig.label
            dst_label = trig.next_trigger

            app_logger.debug(f"Trigger: {src_label} -> {dst_label}")

            if not dst_label or dst_label == src_label:
                if dst_label == src_label:
                    app_logger.warning(f"Skipping self-link: {src_label}")
                continue

            if dst_label in node_map and src_label in node_map:
                self.draw_arrow(node_map[src_label], node_map[dst_label])
            else:
                app_logger.warning(f"Could not find node(s) for arrow: {src_label} -> {dst_label}")

    def draw_arrow(self, start_item, end_item):
        """Draw an arrow from the output anchor of start_item to the input anchor of end_item."""
        start_point = start_item.get_output_anchor()
        end_point = end_item.get_input_anchor()

        app_logger.debug(f"draw_arrow: {start_point} -> {end_point}")

        self.scene.addLine(
            start_point.x(), start_point.y(),
            end_point.x(), end_point.y(),
            QPen(QColor(tp.get("arrow")), 2),
        )

    # ------------------------------------------------------------------
    # Legacy helper (kept for compatibility)
    # ------------------------------------------------------------------

    def add_trigger_node(self, trigger, x, y):
        """Add a single trigger node to the scene at the specified position."""
        node_item = TriggerNodeItem(trigger, x, y)
        self.scene.addItem(node_item)
        app_logger.debug(f"Trigger node for '{trigger.label}' added at ({x}, {y})")

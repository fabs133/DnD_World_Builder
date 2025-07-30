from PyQt5.QtCore import QTimer, QRectF, Qt, QPointF
from PyQt5.QtGui import QBrush, QPen, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QGraphicsTextItem
)
from .trigger_node import TriggerNodeItem 
from typing import List

class TriggerGraphView(QWidget):
    """
    A QWidget that displays a graph of trigger nodes using QGraphicsView and QGraphicsScene.
    Nodes are laid out horizontally and arrows are drawn to represent trigger connections.
    """

    def __init__(self, context=None):
        """
        Initialize the TriggerGraphView.

        :param context: An optional context object containing triggers.
        """
        super().__init__()
        self.context = context
        self.node_items: List[TriggerNodeItem] = []

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.view)
        self.setLayout(self.layout)
        self.next_x = 0
        self.y = 0

        if self.context:
            print(f"[DEBUG - TriggerGraphView] Initializing with context: {context.triggers}")
            self.build_graph(self.context)

    def add_trigger_node(self, trigger, x, y):
        """
        Add a trigger node to the scene at the specified position.

        :param trigger: The trigger object to represent.
        :param x: The x-coordinate for the node.
        :param y: The y-coordinate for the node.
        """
        node_item = TriggerNodeItem(trigger, x, y)
        self.scene.addItem(node_item)
        print(f"[DEBUG - add_trigger_node] Trigger node for '{trigger.label}' added at ({x}, {y})")

    def build_graph(self, context):
        """
        Build the graph layout from the context's triggers.

        :param context: The context object containing triggers.
        """
        if not hasattr(context, "triggers"):
            return

        self.node_items.clear()
        self.scene.clear()

        x, y = 0, 0
        spacing = 220
        print(f"[DEBUG - build_graph] Starting graph layout...")

        for trigger in context.triggers:
            node_item = TriggerNodeItem(trigger, x, y)
            self.scene.addItem(node_item)
            self.node_items.append(node_item)
            print(f"[DEBUG - build_graph] Node '{trigger.label}' placed at ({x}, {y})")
            x += spacing

        self.scene.setSceneRect(0, 0, x + 100, 200)
        self.view.viewport().update()
        self.scene.update()
        QTimer.singleShot(0, lambda: self.manage_graph_building_and_arrows(context))

    def manage_graph_building_and_arrows(self, context):
        """
        Draw arrows between trigger nodes based on their connections.

        :param context: The context object containing triggers.
        """
        print("[DEBUG - manage_graph_building_and_arrows] Starting graph building and arrow drawing process.")
        
        node_map = {node.trigger.label: node for node in self.node_items}

        for trig in context.triggers:
            src_label = trig.label
            dst_label = trig.next_trigger

            print(f"[DEBUG] Trigger: {src_label} → {dst_label}")

            if not dst_label or dst_label == src_label:
                if dst_label == src_label:
                    print(f"[Warning] Skipping self-link: {src_label}")
                continue

            if dst_label in node_map and src_label in node_map:
                self.draw_arrow(node_map[src_label], node_map[dst_label])
            else:
                print(f"[Warning] Could not find node(s) for arrow: {src_label} → {dst_label}")

    def draw_arrow(self, start_item, end_item):
        """
        Draw an arrow (line) from the output anchor of one node to the input anchor of another.

        :param start_item: The starting TriggerNodeItem.
        :param end_item: The ending TriggerNodeItem.
        """
        start_point = start_item.get_output_anchor()
        end_point = end_item.get_input_anchor()

        print(f"[DEBUG - draw_arrow] Start point: {start_point}")
        print(f"[DEBUG - draw_arrow] End point: {end_point}")

        print(f"[DEBUG] start_item.pos(): {start_item.pos()}, end_item.pos(): {end_item.pos()}")
        print(f"[DEBUG] start_item.scenePos(): {start_item.scenePos()}, end_item.scenePos(): {end_item.scenePos()}")

        self.scene.addLine(
            start_point.x() - 175, start_point.y(),
            end_point.x() + 175, end_point.y(),
            QPen(Qt.red, 2)
        )

    def set_context(self, context):
        """
        Set a new context and rebuild the graph.

        :param context: The new context object containing triggers.
        """
        print(f"[DEBUG - set_context] Setting context: {context.triggers}")
        self.context = context
        self.build_graph(self.context)
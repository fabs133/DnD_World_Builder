from PyQt5.QtWidgets import (
    QGraphicsItemGroup, QGraphicsRectItem, QGraphicsTextItem,
    QGraphicsEllipseItem, QGraphicsItem,
)
from PyQt5.QtGui import QBrush, QPen, QColor
from PyQt5.QtCore import QRectF, Qt, QPointF
from core.logger import app_logger
from core import theme_palette as tp

PORT_RADIUS = 6


class TriggerNodeItem(QGraphicsItemGroup):
    """
    A QGraphicsItemGroup representing a trigger node in the editor.

    Displays a colored box with the trigger's event type, condition, and reaction.
    Visual input/output ports allow drag-to-connect wiring in the graph view.

    :param trigger: The trigger object to represent.
    :type trigger: object
    :param x: The x position of the node.
    :type x: float
    :param y: The y position of the node.
    :type y: float
    :param width: The width of the node box.
    :type width: float
    :param height: The height of the node box.
    :type height: float
    """
    def __init__(self, trigger, x, y, width=180, height=100):
        super().__init__()

        self.trigger = trigger
        self.width = width
        self.height = height

        # Node box
        self.box = QGraphicsRectItem(0, 0, width, height)
        self.box.setBrush(QBrush(QColor(tp.get("node_bg"))))
        self.box.setPen(QPen(QColor(tp.get("node_border")), 2))
        self.addToGroup(self.box)

        # Label text lines
        label = f"{trigger.event_type}\n{trigger.condition.__class__.__name__}\n{trigger.reaction.__class__.__name__}"
        for i, line in enumerate(label.split("\n")):
            text_item = QGraphicsTextItem(line)
            text_item.setDefaultTextColor(QColor(tp.get("node_text")))
            text_item.setPos(10, 10 + i * 15)
            self.addToGroup(text_item)

        # Output port — right-centre
        self.output_port = QGraphicsEllipseItem(
            width - PORT_RADIUS, height / 2 - PORT_RADIUS,
            PORT_RADIUS * 2, PORT_RADIUS * 2, self.box
        )
        self.output_port.setBrush(QBrush(QColor(tp.get("arrow"))))
        self.output_port.setPen(QPen(Qt.NoPen))

        # Input port — left-centre
        self.input_port = QGraphicsEllipseItem(
            -PORT_RADIUS, height / 2 - PORT_RADIUS,
            PORT_RADIUS * 2, PORT_RADIUS * 2, self.box
        )
        self.input_port.setBrush(QBrush(QColor(tp.get("node_border"))))
        self.input_port.setPen(QPen(Qt.NoPen))

        # Flags — movable on the canvas, reports position changes
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)

        # Move the whole group after it's fully populated
        self.setPos(x, y)

    # ------------------------------------------------------------------
    # Anchor helpers (used by drag-connect logic in TriggerGraphView)
    # ------------------------------------------------------------------

    def get_output_anchor(self) -> QPointF:
        """
        Get the output anchor point in scene coordinates (right-centre of node).

        :return: Scene-space output anchor.
        :rtype: QPointF
        """
        app_logger.debug(f"TriggerNodeItem output anchor position: ({self.width}, {self.height / 2})")
        return self.mapToScene(QPointF(self.width, self.height / 2))

    def get_input_anchor(self) -> QPointF:
        """
        Get the input anchor point in scene coordinates (left-centre of node).

        :return: Scene-space input anchor.
        :rtype: QPointF
        """
        point = self.mapToScene(QPointF(0, self.height / 2))
        app_logger.debug(f"TriggerNodeItem input anchor position: (0, {self.height / 2})")
        app_logger.debug(f"TriggerNodeItem input anchor (scene): {point}, local pos: {self.pos()}")
        return point

    def output_port_contains(self, scene_pos: QPointF) -> bool:
        """Return True if *scene_pos* is close to the output port."""
        local = self.mapFromScene(scene_pos)
        anchor = QPointF(self.width, self.height / 2)
        return (local - anchor).manhattanLength() <= PORT_RADIUS * 2

    def input_port_contains(self, scene_pos: QPointF) -> bool:
        """Return True if *scene_pos* is close to the input port."""
        local = self.mapFromScene(scene_pos)
        anchor = QPointF(0, self.height / 2)
        return (local - anchor).manhattanLength() <= PORT_RADIUS * 2

    # ------------------------------------------------------------------
    # Label update
    # ------------------------------------------------------------------

    def update_label(self):
        """Update the label text to reflect the current trigger's event, condition, and reaction."""
        for item in self.childItems():
            if isinstance(item, QGraphicsTextItem):
                self.removeFromGroup(item)
                item.scene().removeItem(item)

        label = f"{self.trigger.event_type}\n{self.trigger.condition.__class__.__name__}\n{self.trigger.reaction.__class__.__name__}"
        for i, line in enumerate(label.split("\n")):
            text_item = QGraphicsTextItem(line)
            text_item.setDefaultTextColor(QColor(tp.get("node_text")))
            text_item.setPos(10, 10 + i * 15)
            self.addToGroup(text_item)

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        """Notify the graph view that this node was selected."""
        view = self.scene().views()[0] if self.scene() and self.scene().views() else None
        if view and hasattr(view, "_graph_widget"):
            view._graph_widget.node_selected.emit(self.trigger)
        super().mousePressEvent(event)

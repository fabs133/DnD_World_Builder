from PyQt5.QtWidgets import QGraphicsItemGroup, QGraphicsRectItem, QGraphicsTextItem
from PyQt5.QtGui import QBrush, QPen, QColor
from PyQt5.QtCore import QRectF, Qt, QPointF
from core.logger import app_logger

class TriggerNodeItem(QGraphicsItemGroup):
    """
    A QGraphicsItemGroup representing a trigger node in the editor.

    Displays a colored box with the trigger's event type, condition, and reaction.

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
        """
        Initialize the TriggerNodeItem.

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
        super().__init__()

        self.trigger = trigger
        self.width = width
        self.height = height

        # Create the box first
        self.box = QGraphicsRectItem(0, 0, width, height)
        self.box.setBrush(QBrush(QColor("#ccccff")))
        self.box.setPen(QPen(Qt.black, 2))
        self.addToGroup(self.box)

        # Add label text lines
        label = f"{trigger.event_type}\n{trigger.condition.__class__.__name__}\n{trigger.reaction.__class__.__name__}"
        for i, line in enumerate(label.split("\n")):
            text_item = QGraphicsTextItem(line)
            text_item.setDefaultTextColor(Qt.black)
            text_item.setPos(10, 10 + i * 15)
            self.addToGroup(text_item)

        # 🚨 Now move the whole group *after* it's populated
        self.setPos(x, y)

    def get_output_anchor(self) -> QPointF:
        """
        Get the output anchor point in scene coordinates.

        :return: The output anchor point (right middle of the node).
        :rtype: QPointF
        """
        app_logger.debug(f"TriggerNodeItem output anchor position: ({self.width}, {self.height / 2})")
        return self.mapToScene(QPointF(self.width, self.height / 2))

    def get_input_anchor(self) -> QPointF:
        """
        Get the input anchor point in scene coordinates.

        :return: The input anchor point (left middle of the node).
        :rtype: QPointF
        """
        point = self.mapToScene(QPointF(0, self.height / 2))
        app_logger.debug(f"TriggerNodeItem input anchor position: (0, {self.height / 2})")
        app_logger.debug(f"TriggerNodeItem input anchor (scene): {point}, local pos: {self.pos()}")
        return point

    def update_label(self):
        """
        Update the label text to reflect the current trigger's event, condition, and reaction.
        """
        for item in self.childItems():
            if isinstance(item, QGraphicsTextItem):
                self.removeFromGroup(item)
                item.scene().removeItem(item)

        label = f"{self.trigger.event_type}\n{self.trigger.condition.__class__.__name__}\n{self.trigger.reaction.__class__.__name__}"
        for i, line in enumerate(label.split("\n")):
            text_item = QGraphicsTextItem(line)
            text_item.setDefaultTextColor(Qt.black)
            text_item.setPos(10, 10 + i * 15)
            self.addToGroup(text_item)

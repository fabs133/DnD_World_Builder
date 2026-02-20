from PyQt5.QtWidgets import QGraphicsView
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPainter


class MapView(QGraphicsView):
    """
    Custom QGraphicsView with mouse-wheel zoom and middle-click pan.

    :param parent: Parent widget.
    :type parent: QWidget, optional
    """

    ZOOM_IN_FACTOR = 1.15
    ZOOM_OUT_FACTOR = 1 / 1.15
    MIN_ZOOM = 0.1
    MAX_ZOOM = 10.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom_level = 1.0
        self._panning = False
        self._pan_start = QPointF()
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.NoDrag)

    def wheelEvent(self, event):
        """Zoom in/out on mouse wheel scroll."""
        if event.angleDelta().y() > 0:
            factor = self.ZOOM_IN_FACTOR
        else:
            factor = self.ZOOM_OUT_FACTOR

        new_zoom = self._zoom_level * factor
        if new_zoom < self.MIN_ZOOM or new_zoom > self.MAX_ZOOM:
            return

        self._zoom_level = new_zoom
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        """Start panning on middle-click."""
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Pan the view while middle button is held."""
        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Stop panning on middle-click release."""
        if event.button() == Qt.MiddleButton:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def reset_zoom(self):
        """Reset zoom to 1:1."""
        self.resetTransform()
        self._zoom_level = 1.0

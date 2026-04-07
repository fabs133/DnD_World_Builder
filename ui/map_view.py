from PyQt5.QtWidgets import QGraphicsView
from PyQt5.QtCore import Qt, QPoint, QPointF, QTimeLine, QEasingCurve
from PyQt5.QtGui import QPainter


class MapView(QGraphicsView):
    """
    Custom QGraphicsView with mouse-wheel zoom, middle-click pan,
    and left-click-hold drag-to-pan.

    :param parent: Parent widget.
    :type parent: QWidget, optional
    """

    ZOOM_IN_FACTOR = 1.15
    ZOOM_OUT_FACTOR = 1 / 1.15
    MIN_ZOOM = 0.1
    MAX_ZOOM = 10.0
    _DRAG_THRESHOLD = 5  # pixels before drag activates

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom_level = 1.0
        self._panning = False
        self._pan_start = QPointF()
        # Left-click drag state
        self._drag_panning = False
        self._drag_start = QPointF()
        self._drag_activated = False
        self._auto_fit = False  # When True, auto-fit scene to view on resize
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
        """Start panning on middle-click or prepare left-click drag."""
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.RightButton:
            self._drag_panning = True
            self._drag_start = event.pos()
            self._drag_activated = False
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Pan the view while middle button or left-click drag is held."""
        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
        elif self._drag_panning:
            delta_from_start = event.pos() - self._drag_start
            if not self._drag_activated:
                if (abs(delta_from_start.x()) > self._DRAG_THRESHOLD or
                        abs(delta_from_start.y()) > self._DRAG_THRESHOLD):
                    self._drag_activated = True
                    self._pan_start = event.pos()
                    self.setCursor(Qt.ClosedHandCursor)
                else:
                    super().mouseMoveEvent(event)
                    return
            # Active drag pan
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
        """Stop panning on button release."""
        if event.button() == Qt.MiddleButton:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        elif event.button() == Qt.RightButton:
            self._drag_panning = False
            self._drag_activated = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        """Hide any tooltips when mouse leaves the view."""
        scene = self.scene()
        if scene and hasattr(scene, "_tooltip"):
            scene._tooltip.hide_tooltip()
            scene._tooltip_timer.stop()
        super().leaveEvent(event)

    def set_auto_fit(self, enabled: bool) -> None:
        """When enabled, the scene auto-fits to the view on every resize."""
        self._auto_fit = enabled
        if enabled:
            self._do_auto_fit()

    def refit(self) -> None:
        """Re-run auto-fit (call after fog reveals new tiles)."""
        if self._auto_fit:
            self._do_auto_fit()
            self.viewport().update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._auto_fit:
            self._do_auto_fit()

    def showEvent(self, event):
        super().showEvent(event)
        if self._auto_fit:
            self._do_auto_fit()

    def _do_auto_fit(self):
        scene = self.scene()
        if not scene:
            return

        # Prefer bounding rect of visible items (fog-revealed tiles only)
        # so the map doesn't zoom out to include hidden fog tiles.
        from PyQt5.QtCore import QRectF
        visible_rect = QRectF()
        for item in scene.items():
            if item.isVisible():
                visible_rect = visible_rect.united(item.sceneBoundingRect())

        rect = visible_rect if not visible_rect.isEmpty() else scene.sceneRect()
        if rect.isEmpty():
            return
        vw = self.viewport().width()
        vh = self.viewport().height()
        if vw < 10 or vh < 10:
            return
        # Calculate scale to fit visible content in viewport
        sx = vw / rect.width()
        sy = vh / rect.height()
        scale = min(sx, sy) * 0.90  # 10% padding
        self.resetTransform()
        self.scale(scale, scale)
        self._zoom_level = scale
        self.centerOn(rect.center())

    def reset_zoom(self):
        """Reset zoom to 1:1."""
        self.resetTransform()
        self._zoom_level = 1.0

    def smooth_center_on(self, scene_x: float, scene_y: float,
                         duration_ms: int = 300) -> None:
        """Smoothly scroll the view to center on a scene coordinate."""
        target_view = self.mapFromScene(QPointF(scene_x, scene_y))
        center = QPoint(self.viewport().width() // 2,
                        self.viewport().height() // 2)
        dx = target_view.x() - center.x()
        dy = target_view.y() - center.y()

        if abs(dx) < 2 and abs(dy) < 2:
            return  # already centered

        start_h = self.horizontalScrollBar().value()
        start_v = self.verticalScrollBar().value()

        timeline = QTimeLine(duration_ms, self)
        timeline.setFrameRange(0, 100)
        timeline.setEasingCurve(QEasingCurve.InOutCubic)

        def _step(frame: int) -> None:
            t = frame / 100.0
            self.horizontalScrollBar().setValue(int(start_h + dx * t))
            self.verticalScrollBar().setValue(int(start_v + dy * t))

        timeline.frameChanged.connect(_step)
        timeline.start()

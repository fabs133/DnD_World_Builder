"""Qt animation executor for view transitions.

Reads :class:`~ui.transitions.transition_spec.TransitionSpec` objects
and executes them using ``QPropertyAnimation``.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from PyQt5.QtCore import (
    QEasingCurve, QObject, QPoint, QPropertyAnimation,
    QSequentialAnimationGroup, QTimer, pyqtSignal,
)
from PyQt5.QtWidgets import QGraphicsOpacityEffect, QWidget

from core.logger import app_logger
from ui.transitions.transition_spec import TransitionSpec, TransitionType
from ui.transitions.transition_registry import get_transition


# Map string easing names to QEasingCurve types
_EASING_MAP = {
    "Linear": QEasingCurve.Linear,
    "InQuad": QEasingCurve.InQuad,
    "OutQuad": QEasingCurve.OutQuad,
    "InOutQuad": QEasingCurve.InOutQuad,
    "OutCubic": QEasingCurve.OutCubic,
    "InOutCubic": QEasingCurve.InOutCubic,
    "OutQuart": QEasingCurve.OutQuart,
    "OutBack": QEasingCurve.OutBack,
}


class TransitionEngine(QObject):
    """Executes view transitions from TransitionSpec definitions.

    Signals:
        transition_started(str): Emitted with transition_id.
        transition_completed(str): Emitted when animation finishes.
    """

    transition_started = pyqtSignal(str)
    transition_completed = pyqtSignal(str)

    def __init__(
        self,
        parent_widget: QWidget,
        sound_manager: Any = None,
        theme_engine: Any = None,
    ):
        super().__init__(parent_widget)
        self._parent = parent_widget
        self._sound_manager = sound_manager
        self._theme_engine = theme_engine
        self._active_animation = None

    def execute(
        self,
        transition_id: str,
        outgoing: QWidget | None = None,
        incoming: QWidget | None = None,
        on_complete: Callable | None = None,
    ) -> None:
        """Execute a transition by ID.

        :param transition_id: Registered transition identifier.
        :param outgoing: Widget being replaced (can be None).
        :param incoming: Widget being shown (can be None).
        :param on_complete: Callback fired after transition finishes.
        """
        spec = get_transition(transition_id)
        if spec is None:
            app_logger.warning(f"Unknown transition: {transition_id}")
            self._do_cut(outgoing, incoming)
            if on_complete:
                on_complete()
            return

        self.transition_started.emit(transition_id)

        # Play sound
        if spec.sound_id and self._sound_manager:
            from core.audio.ui_sound_manager import SoundCategory
            cat = SoundCategory(spec.sound_category) if spec.sound_category else SoundCategory.UI
            self._sound_manager.play(spec.sound_id, cat)

        # Dispatch by type
        if spec.transition_type == TransitionType.CUT:
            self._do_cut(outgoing, incoming)
            self._finish(transition_id, spec, on_complete)

        elif spec.transition_type == TransitionType.FADE:
            self._do_fade(outgoing, incoming, spec, transition_id, on_complete)

        elif spec.transition_type == TransitionType.SLIDE:
            self._do_slide(outgoing, incoming, spec, transition_id, on_complete)

        elif spec.transition_type == TransitionType.ZOOM:
            self._do_fade(outgoing, incoming, spec, transition_id, on_complete)

        elif spec.transition_type == TransitionType.CINEMATIC:
            self._do_cinematic(outgoing, incoming, spec, transition_id, on_complete)

    # ── Transition implementations ───────────────────────────────────

    def _do_cut(self, outgoing: QWidget | None, incoming: QWidget | None) -> None:
        if outgoing:
            outgoing.hide()
        if incoming:
            incoming.show()

    def _do_fade(
        self, outgoing, incoming, spec, transition_id, on_complete
    ) -> None:
        duration = spec.duration_ms

        if outgoing:
            effect = QGraphicsOpacityEffect(outgoing)
            outgoing.setGraphicsEffect(effect)
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(duration // 2)
            anim.setStartValue(1.0)
            anim.setEndValue(0.0)
            anim.setEasingCurve(self._get_easing(spec.easing))

            def _on_fade_out_done():
                outgoing.hide()
                outgoing.setGraphicsEffect(None)
                if incoming:
                    in_effect = QGraphicsOpacityEffect(incoming)
                    incoming.setGraphicsEffect(in_effect)
                    incoming.show()
                    in_anim = QPropertyAnimation(in_effect, b"opacity")
                    in_anim.setDuration(duration // 2)
                    in_anim.setStartValue(0.0)
                    in_anim.setEndValue(1.0)
                    in_anim.setEasingCurve(self._get_easing(spec.easing))
                    in_anim.finished.connect(
                        lambda: self._cleanup_fade(incoming, transition_id, spec, on_complete)
                    )
                    self._active_animation = in_anim
                    in_anim.start()
                else:
                    self._finish(transition_id, spec, on_complete)

            anim.finished.connect(_on_fade_out_done)
            self._active_animation = anim
            anim.start()
        elif incoming:
            effect = QGraphicsOpacityEffect(incoming)
            incoming.setGraphicsEffect(effect)
            incoming.show()
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(duration)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(self._get_easing(spec.easing))
            anim.finished.connect(
                lambda: self._cleanup_fade(incoming, transition_id, spec, on_complete)
            )
            self._active_animation = anim
            anim.start()
        else:
            self._finish(transition_id, spec, on_complete)

    def _cleanup_fade(self, widget, transition_id, spec, on_complete):
        if widget:
            widget.setGraphicsEffect(None)
        self._finish(transition_id, spec, on_complete)

    def _do_slide(
        self, outgoing, incoming, spec, transition_id, on_complete
    ) -> None:
        duration = spec.duration_ms
        w = self._parent.width()
        h = self._parent.height()

        offsets = {
            "left": QPoint(-w, 0),
            "right": QPoint(w, 0),
            "up": QPoint(0, -h),
            "down": QPoint(0, h),
        }
        offset = offsets.get(spec.direction, QPoint(-w, 0))

        if outgoing:
            start_pos = outgoing.pos()
            anim = QPropertyAnimation(outgoing, b"pos")
            anim.setDuration(duration)
            anim.setStartValue(start_pos)
            anim.setEndValue(start_pos + offset)
            anim.setEasingCurve(self._get_easing(spec.easing))
            anim.finished.connect(lambda: outgoing.hide())
            self._active_animation = anim
            anim.start()

        if incoming:
            target_pos = incoming.pos()
            incoming.move(target_pos - offset)
            incoming.show()
            anim = QPropertyAnimation(incoming, b"pos")
            anim.setDuration(duration)
            anim.setStartValue(target_pos - offset)
            anim.setEndValue(target_pos)
            anim.setEasingCurve(self._get_easing(spec.easing))
            anim.finished.connect(
                lambda: self._finish(transition_id, spec, on_complete)
            )
            self._active_animation = anim
            anim.start()
        elif outgoing:
            QTimer.singleShot(duration, lambda: self._finish(transition_id, spec, on_complete))
        else:
            self._finish(transition_id, spec, on_complete)

    def _do_cinematic(
        self, outgoing, incoming, spec, transition_id, on_complete
    ) -> None:
        """Multi-phase cinematic transition.

        Shake → cut to black → hold → theme swap → incoming rises → settle.
        """
        # Phase A: hide outgoing immediately (simplified shake)
        if outgoing:
            outgoing.hide()

        # Phase B+C: hold black, swap theme during hold
        def _after_hold():
            # Theme swap during black
            if spec.theme_after and self._theme_engine:
                from core.theme_engine import ThemeMode
                mode = ThemeMode(spec.theme_after)
                self._theme_engine.swap_to(mode)

            # Phase D: show incoming
            if incoming:
                incoming.show()

            self._finish(transition_id, spec, on_complete)

        hold_ms = max(spec.hold_black_ms, 50)
        QTimer.singleShot(hold_ms, _after_hold)

    # ── Helpers ───────────────────────────────────────────────────────

    def _finish(
        self,
        transition_id: str,
        spec: TransitionSpec | None,
        on_complete: Callable | None,
    ) -> None:
        self._active_animation = None
        self.transition_completed.emit(transition_id)
        if on_complete:
            on_complete()

    @staticmethod
    def _get_easing(name: str) -> QEasingCurve:
        return QEasingCurve(_EASING_MAP.get(name, QEasingCurve.OutQuart))

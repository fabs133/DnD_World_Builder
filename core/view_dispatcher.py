"""Central non-blocking dispatcher for view side-effects.

Every subsystem (audio, animation, network) registers a worker.
Signal handlers call ``dispatch()`` which returns *instantly* —
the heavy work is handed off to the appropriate worker thread or
queued for the next GUI-idle window.

This prevents any single subsystem from blocking the Qt event loop
and swallowing user input.

Usage::

    from core.view_dispatcher import ViewDispatcher, Effect, EffectType

    # In a signal handler (runs on GUI thread):
    ViewDispatcher.instance().dispatch(
        Effect(EffectType.AUDIO, "play", path="/sounds/hit.wav", channel="sfx")
    )
    # Returns immediately — audio work happens on the audio thread.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from PyQt5.QtCore import QMetaObject, QObject, Qt, QThread, QTimer, pyqtSignal, pyqtSlot
    from PyQt5.QtWidgets import QApplication

    _HAS_QT = True
except ImportError:
    _HAS_QT = False

    class QObject:  # type: ignore[no-redef]
        def __init__(self, *a, **kw):
            pass

    def pyqtSlot(*a, **kw):  # type: ignore[no-redef]
        def _dec(fn):
            return fn
        return _dec


class EffectType(Enum):
    """Categories of deferred work."""

    AUDIO = "audio"
    ANIMATION = "animation"
    NETWORK = "network"
    UI = "ui"


@dataclass
class Effect:
    """Lightweight command representing deferred work.

    :param effect_type: Which subsystem should handle this.
    :param action: Action identifier (e.g. ``"play"``, ``"stop"``).
    :param params: Arbitrary parameters for the handler.
    :param callback: Optional GUI-thread callback after completion.
    """

    effect_type: EffectType
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable[[], None]] = None


class _WorkerBase(QObject):
    """Base class for subsystem workers that live on their own thread."""

    done = pyqtSignal(object) if _HAS_QT else None

    def handle(self, effect: Effect) -> None:
        """Override in subclasses to process an effect."""
        raise NotImplementedError


class ViewDispatcher(QObject):
    """Central non-blocking effect dispatcher.

    - **Threaded workers** (AUDIO, NETWORK): effects are handed off to a
      dedicated ``QThread`` via queued signal.  The GUI thread does zero
      heavy work — just enqueues and returns.
    - **GUI-deferred queue** (ANIMATION, UI): effects are appended to a
      drain queue and processed during the next idle window (≤8 ms budget
      per frame at ~60 fps).

    Must be created on the GUI thread.
    """

    _instance: Optional["ViewDispatcher"] = None

    # Internal signal to hand work to a worker on another thread
    _dispatch_to_worker = pyqtSignal(object, object) if _HAS_QT else None

    @classmethod
    def instance(cls) -> Optional["ViewDispatcher"]:
        return cls._instance

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # Workers keyed by EffectType
        self._workers: Dict[EffectType, _WorkerBase] = {}
        self._threads: Dict[EffectType, QThread] = {}

        # GUI-deferred queue for UI / animation effects
        self._gui_queue: deque[Effect] = deque()

        if _HAS_QT:
            self._drain_timer = QTimer(self)
            self._drain_timer.timeout.connect(self._drain_gui_queue)
            self._drain_timer.start(16)  # ~60 fps

    # ------------------------------------------------------------------
    # Worker registration
    # ------------------------------------------------------------------

    def register_worker(
        self,
        effect_type: EffectType,
        worker: _WorkerBase,
        threaded: bool = True,
    ) -> None:
        """Register a worker for an effect type.

        :param threaded: If True, the worker is moved to its own QThread.
            If False, effects are queued for GUI-thread drain (same as UI).
        """
        self._workers[effect_type] = worker

        if threaded and _HAS_QT:
            thread = QThread(self)
            thread.setObjectName(f"dispatcher-{effect_type.value}")
            worker.moveToThread(thread)
            thread.start()
            self._threads[effect_type] = thread
            logger.info(
                "[ViewDispatcher] Worker '%s' on thread '%s'",
                effect_type.value,
                thread.objectName(),
            )
        else:
            logger.info(
                "[ViewDispatcher] Worker '%s' on GUI thread (deferred)",
                effect_type.value,
            )

        # Connect completion callback routing
        if hasattr(worker, "done") and worker.done is not None:
            worker.done.connect(self._on_worker_done)

    # ------------------------------------------------------------------
    # Dispatch (the hot path — must be fast)
    # ------------------------------------------------------------------

    def dispatch(self, effect: Effect) -> None:
        """Non-blocking dispatch.  Returns immediately.

        - If the effect type has a threaded worker → hand off via
          ``QMetaObject.invokeMethod`` (queued connection).
        - Otherwise → append to GUI drain queue.
        """
        worker = self._workers.get(effect.effect_type)

        if worker is not None and effect.effect_type in self._threads:
            # Hand off to worker thread — zero blocking on GUI thread
            QMetaObject.invokeMethod(
                worker,
                "_handle_effect",
                Qt.QueuedConnection,
            )
            # We can't pass arbitrary Python objects through invokeMethod
            # easily, so use a thread-safe queue on the worker instead.
            if hasattr(worker, "_effect_queue"):
                worker._effect_queue.append(effect)
            return

        # GUI-deferred: queue for next drain cycle
        self._gui_queue.append(effect)

    # ------------------------------------------------------------------
    # GUI drain (runs every ~16ms, budgeted to ≤8ms)
    # ------------------------------------------------------------------

    @pyqtSlot()
    def _drain_gui_queue(self) -> None:
        if not self._gui_queue:
            return

        deadline = time.monotonic() + 0.008  # 8ms budget
        while self._gui_queue and time.monotonic() < deadline:
            effect = self._gui_queue.popleft()
            worker = self._workers.get(effect.effect_type)
            if worker is not None:
                try:
                    worker.handle(effect)
                except Exception:
                    logger.exception(
                        "[ViewDispatcher] GUI worker error for %s/%s",
                        effect.effect_type.value,
                        effect.action,
                    )
            # Fire completion callback if present
            if effect.callback is not None:
                try:
                    effect.callback()
                except Exception:
                    logger.exception("[ViewDispatcher] Callback error")

    # ------------------------------------------------------------------
    # Worker completion (forwarded to GUI thread)
    # ------------------------------------------------------------------

    @pyqtSlot(object)
    def _on_worker_done(self, result: object) -> None:
        """Called on GUI thread when a worker emits ``done``."""
        # result can carry a callback or data for the UI
        if callable(result):
            result()

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Stop all worker threads gracefully."""
        for effect_type, thread in self._threads.items():
            worker = self._workers.get(effect_type)
            # Invoke cleanup on the worker thread so timers are stopped
            # from the thread that owns them
            if worker and hasattr(worker, "cleanup"):
                QMetaObject.invokeMethod(
                    worker, "cleanup", Qt.BlockingQueuedConnection,
                )
            logger.info("[ViewDispatcher] Stopping thread '%s'", effect_type.value)
            thread.quit()
            thread.wait(2000)
        self._threads.clear()
        self._workers.clear()
        if hasattr(self, "_drain_timer"):
            self._drain_timer.stop()

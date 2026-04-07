"""LRU asset cache with background image loading.

``QPixmap`` creation must happen on the GUI thread (Qt restriction).
The background worker loads raw ``QImage`` data off-thread, then the
GUI thread converts it to ``QPixmap`` and stores it in the cache.

Usage::

    from core.asset_cache import AssetCache

    # Synchronous (cache hit or None):
    pm = AssetCache.instance().get(path)

    # Async with callback (cache hit returns immediately, miss loads in bg):
    pm = AssetCache.instance().request(path, callback=self._on_loaded)
    if pm is not None:
        self._use(pm)  # was cached
    # else: callback fires on GUI thread when ready
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

try:
    from PyQt5.QtCore import QObject, QRunnable, QThreadPool, QMetaObject, Qt, pyqtSignal, pyqtSlot
    from PyQt5.QtGui import QImage, QPixmap

    _HAS_QT = True
except ImportError:
    _HAS_QT = False

    class QObject:  # type: ignore[no-redef]
        def __init__(self, *a, **kw):
            pass


class _ImageLoadTask(QRunnable):
    """Loads a QImage from disk on a thread pool thread."""

    def __init__(self, path: str, cache: "AssetCache") -> None:
        super().__init__()
        self._path = path
        self._cache = cache
        self.setAutoDelete(True)

    def run(self) -> None:
        image = QImage(self._path)
        if image.isNull():
            logger.warning("[AssetCache] Failed to load: %s", self._path)
            return
        # Marshal back to GUI thread
        QMetaObject.invokeMethod(
            self._cache,
            "_on_image_loaded",
            Qt.QueuedConnection,
        )
        # Store the loaded image for the GUI thread to pick up
        self._cache._loaded_images[self._path] = image


class AssetCache(QObject):
    """Singleton LRU cache for QPixmap assets with background preloading.

    - ``get(path)`` — instant cache lookup, returns ``QPixmap | None``
    - ``request(path, callback)`` — returns cached pixmap or starts bg load
    - Cache evicts LRU entries beyond ``MAX_ENTRIES``
    """

    _instance: Optional["AssetCache"] = None

    MAX_ENTRIES = 200

    asset_ready = pyqtSignal(str, object) if _HAS_QT else None

    @classmethod
    def instance(cls) -> Optional["AssetCache"]:
        return cls._instance

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._cache: OrderedDict[str, QPixmap] = OrderedDict()
        self._pending: Set[str] = set()
        self._callbacks: Dict[str, List[Callable]] = {}
        self._loaded_images: Dict[str, QImage] = {}

        if _HAS_QT:
            self._pool = QThreadPool.globalInstance()

    def get(self, path: str) -> Optional[QPixmap]:
        """Return cached pixmap immediately, or None."""
        if not _HAS_QT or not path:
            return None
        key = str(Path(path).resolve())
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def request(
        self,
        path: str,
        callback: Optional[Callable[[str, QPixmap], None]] = None,
    ) -> Optional[QPixmap]:
        """Return pixmap if cached; otherwise start background load.

        :param callback: Called on GUI thread with ``(path, pixmap)`` when ready.
        :returns: Cached ``QPixmap`` or ``None`` if loading in background.
        """
        if not _HAS_QT or not path:
            return None

        key = str(Path(path).resolve())

        cached = self.get(key)
        if cached is not None:
            return cached

        if callback:
            self._callbacks.setdefault(key, []).append(callback)

        if key not in self._pending:
            self._pending.add(key)
            task = _ImageLoadTask(key, self)
            self._pool.start(task)

        return None

    def put(self, path: str, pixmap: QPixmap) -> None:
        """Manually insert a pixmap into the cache."""
        if not _HAS_QT or not path:
            return
        key = str(Path(path).resolve())
        self._cache[key] = pixmap
        self._cache.move_to_end(key)
        self._evict()

    @pyqtSlot()
    def _on_image_loaded(self) -> None:
        """Process images loaded by background threads."""
        # Drain all loaded images
        while self._loaded_images:
            path, image = self._loaded_images.popitem()
            pixmap = QPixmap.fromImage(image)
            if pixmap.isNull():
                self._pending.discard(path)
                continue

            self._cache[path] = pixmap
            self._cache.move_to_end(path)
            self._evict()
            self._pending.discard(path)

            # Fire callbacks
            for cb in self._callbacks.pop(path, []):
                try:
                    cb(path, pixmap)
                except Exception:
                    logger.exception("[AssetCache] Callback error for %s", path)

            if self.asset_ready is not None:
                self.asset_ready.emit(path, pixmap)

    def _evict(self) -> None:
        while len(self._cache) > self.MAX_ENTRIES:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        """Clear the entire cache."""
        self._cache.clear()
        self._pending.clear()
        self._callbacks.clear()
        self._loaded_images.clear()

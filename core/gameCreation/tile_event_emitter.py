from PyQt5.QtCore import QObject, pyqtSignal

class TileEventEmitter(QObject):
    """
    TileEventEmitter is a QObject subclass that provides custom signals for tile-related events.

    Signals:
        The `right_clicked` signal is emitted when a tile is right-clicked, passing the tile object.
        The `hover_entered` signal is emitted when the mouse enters a tile, passing the tile object.
        The `hover_left` signal is emitted when the mouse leaves a tile, passing the tile object.
    """

    right_clicked = pyqtSignal(object)  # Emits the tile itself
    hover_entered = pyqtSignal(object)
    hover_left = pyqtSignal(object)

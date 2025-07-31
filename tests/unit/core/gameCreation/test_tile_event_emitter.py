import sys
import pytest
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication
from core.gameCreation.tile_event_emitter import TileEventEmitter

# Ensure QApplication is present (especially for CI environments)
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

# ---- Test 1 ----

def test_tile_event_emitter_is_qobject():
    emitter = TileEventEmitter()
    assert isinstance(emitter, QObject)

# ---- Test 2 ----

def test_signals_emitted_and_receive_payload():
    emitter = TileEventEmitter()
    received = []

    # Connect signals to capture emissions
    emitter.right_clicked.connect(lambda tile: received.append(('right', tile)))
    emitter.hover_entered.connect(lambda tile: received.append(('enter', tile)))
    emitter.hover_left.connect(lambda tile: received.append(('left', tile)))

    # Emit with different payloads
    obj = object()
    emitter.right_clicked.emit(obj)
    emitter.hover_entered.emit(123)
    emitter.hover_left.emit("tile")

    # Verify all signals delivered
    assert received == [
        ('right', obj),
        ('enter', 123),
        ('left', 'tile')
    ]

# ---- Test 3 ----
# Replaces qtbot.waitSignal() with direct signal assertion

@pytest.mark.parametrize("signal_name,payload", [
    ("right_clicked", None),
    ("hover_entered", 'payload'),
    ("hover_left", 3.14)
])
def test_signal_can_emit_various_types(signal_name, payload):
    emitter = TileEventEmitter()
    captured = []

    sig = getattr(emitter, signal_name)
    sig.connect(lambda value: captured.append(value))
    sig.emit(payload)

    assert captured == [payload]

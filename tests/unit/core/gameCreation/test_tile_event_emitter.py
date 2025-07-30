import pytest
from PyQt5.QtCore import QObject
from core.gameCreation.tile_event_emitter import TileEventEmitter


def test_tile_event_emitter_is_qobject():
    emitter = TileEventEmitter()
    assert isinstance(emitter, QObject)


def test_signals_emitted_and_receive_payload(qtbot):
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

@pytest.mark.parametrize("signal_name,payload", [
    ("right_clicked", None),
    ("hover_entered", 'payload'),
    ("hover_left", 3.14)
])
def test_signal_can_emit_various_types(qtbot, signal_name, payload):
    emitter = TileEventEmitter()

    # Dynamically get the Qt signal
    sig = getattr(emitter, signal_name)

    # Use qtbot.waitSignal to process the emission
    with qtbot.waitSignal(sig, timeout=500) as blocker:
        sig.emit(payload)

    # Verify the signal args
    assert blocker.args == [payload]

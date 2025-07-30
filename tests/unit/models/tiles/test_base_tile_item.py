import pytest
from PyQt5.QtWidgets import QGraphicsItem

from models.tiles.base_tile_item import BaseTileItem  # adjust this import if your file lives elsewhere

def test_inheritance_and_defaults(qapp):
    # qapp fixture ensures a QApplication is running
    item = BaseTileItem()
    # It must be a QGraphicsItem
    assert isinstance(item, QGraphicsItem)
    # Initial attributes should be empty, and no emitter set
    assert item.attributes == {}
    assert item.event_emitter is None

@pytest.mark.parametrize("method_name", [
    "handle_hover_enter",
    "handle_hover_leave",
    "handle_right_click",
])
def test_abstract_methods_raise_not_implemented(qapp, method_name):
    item = BaseTileItem()
    method = getattr(item, method_name)
    with pytest.raises(NotImplementedError) as exc:
        method(event=None)
    # The exception message should mention the method
    assert method_name in str(exc.value)

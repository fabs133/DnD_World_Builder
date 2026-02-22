import pytest
from PyQt5.QtCore import QPointF

from ui.dialogs.trigger_editor.trigger_node import TriggerNodeItem, PORT_RADIUS


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

class _Cond:
    pass


class _React:
    pass


class FakeTrigger:
    def __init__(self, label="test_trigger"):
        self.label = label
        self.event_type = "ENTER_TILE"
        self.condition = _Cond()
        self.reaction = _React()
        self.next_trigger = None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def node(qapp):
    return TriggerNodeItem(FakeTrigger(), x=0, y=0)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_node_stores_trigger(node):
    assert node.trigger is not None
    assert node.trigger.label == "test_trigger"


def test_node_default_dimensions(node):
    assert node.width == 180
    assert node.height == 100


def test_node_custom_dimensions(qapp):
    n = TriggerNodeItem(FakeTrigger(), x=10, y=20, width=200, height=120)
    assert n.width == 200
    assert n.height == 120


def test_node_positioned_correctly(qapp):
    n = TriggerNodeItem(FakeTrigger(), x=50, y=30)
    assert n.pos().x() == pytest.approx(50)
    assert n.pos().y() == pytest.approx(30)


# ---------------------------------------------------------------------------
# Anchor helpers
# ---------------------------------------------------------------------------

def test_get_output_anchor_returns_right_centre(node):
    anchor = node.get_output_anchor()
    # Node at (0, 0) — output is at (width, height/2) in scene coords
    assert anchor.x() == pytest.approx(node.width)
    assert anchor.y() == pytest.approx(node.height / 2)


def test_get_input_anchor_returns_left_centre(node):
    anchor = node.get_input_anchor()
    assert anchor.x() == pytest.approx(0)
    assert anchor.y() == pytest.approx(node.height / 2)


def test_anchors_shift_with_node_position(qapp):
    n = TriggerNodeItem(FakeTrigger(), x=100, y=50)
    out = n.get_output_anchor()
    inp = n.get_input_anchor()
    assert out.x() == pytest.approx(100 + n.width)
    assert out.y() == pytest.approx(50 + n.height / 2)
    assert inp.x() == pytest.approx(100)
    assert inp.y() == pytest.approx(50 + n.height / 2)


# ---------------------------------------------------------------------------
# Port hit-detection
# ---------------------------------------------------------------------------

def test_output_port_contains_centre_point(node):
    centre = QPointF(node.width, node.height / 2)
    assert node.output_port_contains(centre)


def test_output_port_does_not_contain_far_point(node):
    far = QPointF(0, 0)
    assert not node.output_port_contains(far)


def test_input_port_contains_centre_point(node):
    centre = QPointF(0, node.height / 2)
    assert node.input_port_contains(centre)


def test_input_port_does_not_contain_far_point(node):
    far = QPointF(node.width, node.height / 2)
    assert not node.input_port_contains(far)


def test_output_port_contains_within_manhattan_radius(node):
    # Point just inside the 2*PORT_RADIUS manhattan boundary
    near = QPointF(node.width - PORT_RADIUS, node.height / 2)
    assert node.output_port_contains(near)


# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------

def test_node_is_movable(node):
    from PyQt5.QtWidgets import QGraphicsItem
    assert node.flags() & QGraphicsItem.ItemIsMovable


def test_node_sends_position_changes(node):
    from PyQt5.QtWidgets import QGraphicsItem
    assert node.flags() & QGraphicsItem.ItemSendsScenePositionChanges

import pytest
import PyQt5.QtCore as qc

from ui.dialogs.trigger_editor.graph_view import TriggerGraphView, COLUMN_WIDTH


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

class _Cond:
    pass


class _React:
    pass


class FakeTrigger:
    def __init__(self, label, next_trigger=None):
        self.label = label
        self.event_type = "ENTER_TILE"
        self.condition = _Cond()
        self.reaction = _React()
        self.next_trigger = next_trigger


class FakeContext:
    def __init__(self, triggers=None):
        self.triggers = list(triggers or [])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def no_timer(monkeypatch):
    monkeypatch.setattr(qc.QTimer, "singleShot", lambda *a, **k: None)


@pytest.fixture
def gv(qapp):
    return TriggerGraphView()


# ---------------------------------------------------------------------------
# _assign_columns — BFS ordering
# ---------------------------------------------------------------------------

def test_assign_columns_single_trigger(gv):
    t = FakeTrigger("A")
    col = gv._assign_columns([t])
    assert col["A"] == 0


def test_assign_columns_linear_chain(gv):
    t1 = FakeTrigger("A", next_trigger="B")
    t2 = FakeTrigger("B", next_trigger="C")
    t3 = FakeTrigger("C")
    col = gv._assign_columns([t1, t2, t3])
    assert col["A"] == 0
    assert col["B"] == 1
    assert col["C"] == 2


def test_assign_columns_disconnected_get_fallback(gv):
    t1 = FakeTrigger("A")
    t2 = FakeTrigger("B")  # No chain — two separate roots
    col = gv._assign_columns([t1, t2])
    # Both are roots (nothing points at them) so both land in col 0 via BFS
    # They get distinct columns due to fallback logic only if unvisited
    assert col["A"] == 0
    assert col["B"] == 0  # two independent roots both start at col 0


def test_assign_columns_empty(gv):
    col = gv._assign_columns([])
    assert col == {}


def test_assign_columns_unknown_next_trigger_ignored(gv):
    t = FakeTrigger("A", next_trigger="GHOST")
    col = gv._assign_columns([t])
    assert col["A"] == 0


# ---------------------------------------------------------------------------
# build_graph — node placement
# ---------------------------------------------------------------------------

def test_build_graph_creates_correct_node_count(qapp, monkeypatch):
    monkeypatch.setattr(qc.QTimer, "singleShot", lambda *a, **k: None)
    gv = TriggerGraphView()
    ctx = FakeContext([FakeTrigger("X"), FakeTrigger("Y"), FakeTrigger("Z")])
    gv.build_graph(ctx)
    assert len(gv.node_items) == 3


def test_build_graph_positions_chained_nodes_in_columns(qapp, monkeypatch):
    monkeypatch.setattr(qc.QTimer, "singleShot", lambda *a, **k: None)
    gv = TriggerGraphView()
    t1 = FakeTrigger("A", next_trigger="B")
    t2 = FakeTrigger("B")
    ctx = FakeContext([t1, t2])
    gv.build_graph(ctx)
    node_a = next(n for n in gv.node_items if n.trigger.label == "A")
    node_b = next(n for n in gv.node_items if n.trigger.label == "B")
    assert node_b.pos().x() - node_a.pos().x() == pytest.approx(COLUMN_WIDTH)


def test_build_graph_clears_previous_nodes(qapp, monkeypatch):
    monkeypatch.setattr(qc.QTimer, "singleShot", lambda *a, **k: None)
    gv = TriggerGraphView()
    ctx1 = FakeContext([FakeTrigger("A"), FakeTrigger("B")])
    ctx2 = FakeContext([FakeTrigger("C")])
    gv.build_graph(ctx1)
    gv.build_graph(ctx2)
    assert len(gv.node_items) == 1
    assert gv.node_items[0].trigger.label == "C"


def test_build_graph_with_empty_context(qapp, monkeypatch):
    monkeypatch.setattr(qc.QTimer, "singleShot", lambda *a, **k: None)
    gv = TriggerGraphView()
    gv.build_graph(FakeContext([]))
    assert gv.node_items == []


# ---------------------------------------------------------------------------
# refresh
# ---------------------------------------------------------------------------

def test_refresh_rebuilds_graph(qapp, monkeypatch):
    monkeypatch.setattr(qc.QTimer, "singleShot", lambda *a, **k: None)
    gv = TriggerGraphView()
    ctx = FakeContext([FakeTrigger("A")])
    gv.set_context(ctx)
    assert len(gv.node_items) == 1
    ctx.triggers.append(FakeTrigger("B"))
    gv.refresh()
    assert len(gv.node_items) == 2


def test_refresh_noop_without_context(qapp):
    gv = TriggerGraphView()
    gv.refresh()   # should not raise

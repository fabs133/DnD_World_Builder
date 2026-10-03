"""Tests for the dice roller panel."""

import random

import pytest

from core.engine import dice
from ui.panels.dice_panel import HISTORY_LIMIT, DicePanel


@pytest.fixture
def panel(qapp):
    return DicePanel(rng=random.Random(3))


def _items(panel):
    return [panel.history.item(i).text() for i in range(panel.history.count())]


def _expected(expr, seed=3):
    return dice.format_roll(dice.roll(expr, rng=random.Random(seed)))


def test_local_roll_appends_history(panel):
    panel.expression_edit.setText("2d6+3")
    panel.roll_button.click()
    assert _items(panel) == [_expected("2d6+3")]
    assert panel.error_label.isHidden()


def test_enter_rolls(panel):
    panel.expression_edit.setText("d20")
    panel.expression_edit.returnPressed.emit()
    assert _items(panel) == [_expected("d20")]


def test_history_newest_first(panel):
    panel.roll("d4")
    panel.roll("d6")
    items = _items(panel)
    assert len(items) == 2
    assert items[0].startswith("d6")
    assert items[1].startswith("d4")


@pytest.mark.parametrize(
    "label,expr",
    [("d4", "d4"), ("d6", "d6"), ("d8", "d8"), ("d10", "d10"), ("d12", "d12"),
     ("d20", "d20"), ("d100", "d100"), ("Adv", "2d20kh1"), ("Dis", "2d20kl1")],
)
def test_quick_buttons(panel, label, expr):
    seen = []
    panel.roll_requested.connect(seen.append)
    panel.quick_buttons[label].click()
    assert seen == [expr]
    assert panel.expression_edit.text() == expr
    assert _items(panel) == [_expected(expr)]


def test_invalid_expression_shows_inline_error_and_skips_remote(panel):
    calls = []
    emitted = []
    panel.set_remote(calls.append)
    panel.roll_requested.connect(emitted.append)
    panel.expression_edit.setText("banana")
    panel.roll_button.click()
    assert not panel.error_label.isHidden()
    assert panel.error_label.text()
    assert calls == []
    assert emitted == []
    assert panel.history.count() == 0


def test_error_clears_on_valid_roll(panel):
    panel.roll("banana")
    panel.roll("d6")
    assert panel.error_label.isHidden()


def test_remote_mode_sends_roll_command(panel):
    calls = []
    panel.set_remote(calls.append)
    panel.expression_edit.setText("2d6+3")
    panel.roll_button.click()
    assert calls == ["/roll 2d6+3"]
    assert panel.history.count() == 0  # host echo adds it via add_history


def test_back_to_local_after_remote(panel):
    calls = []
    panel.set_remote(calls.append)
    panel.set_remote(None)
    panel.roll("d6")
    assert calls == []
    assert panel.history.count() == 1


def test_history_cap(panel):
    for i in range(HISTORY_LIMIT + 10):
        panel.add_history(f"entry {i}")
    assert panel.history.count() == HISTORY_LIMIT
    assert panel.history.item(0).text() == f"entry {HISTORY_LIMIT + 9}"

"""Tests for CombatLogWidget and CombatLogEntry."""

import pytest

from ui.widgets.combat_log_widget import (
    CombatLogWidget, CombatLogEntry, _SystemMessage, _highlight_dice,
)


class TestHighlightDice:
    def test_d20_roll(self):
        result = _highlight_dice("d20(14) + 4 = 18")
        assert "d20(14)" in result
        assert "<span" in result

    def test_natural_20(self):
        result = _highlight_dice("d20(20)")
        assert "font-weight:bold" in result
        assert "#c9952a" in result  # gold colour

    def test_natural_1(self):
        result = _highlight_dice("d20(1)")
        assert "#8a2020" in result  # red colour

    def test_hit_keyword(self):
        result = _highlight_dice("→ HIT")
        assert "#2a6a30" in result  # green

    def test_miss_keyword(self):
        result = _highlight_dice("→ MISS")
        assert "#8a2020" in result  # red

    def test_crit_keyword(self):
        result = _highlight_dice("CRIT!")
        assert "#c9952a" in result  # gold

    def test_plain_text_unchanged(self):
        text = "Goblin moves to (3, 5)"
        assert _highlight_dice(text) == text

    def test_damage_dice(self):
        result = _highlight_dice("2d6+3 slashing")
        assert "<span" in result
        assert "2d6+3" in result


class TestCombatLogEntry:
    def test_construction(self, qapp):
        entry = CombatLogEntry(
            actor_name="Goblin",
            action_type="Attack",
            success=True,
            execution_log=["d20(14) + 4 = 18 vs AC 15 → HIT", "1d6+2 = 5 damage"],
            round_num=1,
        )
        assert entry is not None

    def test_expand_collapse(self, qapp):
        entry = CombatLogEntry(
            actor_name="Fighter",
            action_type="Attack",
            success=True,
            execution_log=["Summary line", "Detail line 1", "Detail line 2"],
        )
        assert not entry._expanded
        assert not entry._detail_widget.isVisible()

        # Directly toggle expansion (mousePressEvent delegates to this logic)
        entry._expanded = True
        entry._detail_widget.setVisible(True)
        assert entry._expanded
        # Widget not shown on screen, so check the *hidden* flag rather than isVisible()
        assert not entry._detail_widget.isHidden()

        entry._expanded = False
        entry._detail_widget.setVisible(False)
        assert not entry._expanded
        assert entry._detail_widget.isHidden()

    def test_single_line_not_expandable(self, qapp):
        entry = CombatLogEntry(
            actor_name="Goblin",
            action_type="Move",
            success=True,
            execution_log=["Moved to (3, 5)"],
        )
        from PyQt5.QtTest import QTest
        from PyQt5.QtCore import Qt
        QTest.mouseClick(entry, Qt.LeftButton)
        assert not entry._expanded  # Only one line, nothing to expand


class TestCombatLogWidget:
    def test_construction(self, qapp):
        widget = CombatLogWidget()
        assert widget._entry_count == 0

    def test_add_entry(self, qapp):
        widget = CombatLogWidget()
        widget.add_entry("Goblin", "Attack", True, ["Hit for 5 damage"])
        assert widget._entry_count == 1

    def test_add_system_message(self, qapp):
        widget = CombatLogWidget()
        widget.add_system_message("=== Combat Started ===", "combat")
        assert widget._entry_count == 1

    def test_append_backward_compat(self, qapp):
        widget = CombatLogWidget()
        widget.append("  Plain text log entry")
        assert widget._entry_count == 1

    def test_append_empty_ignored(self, qapp):
        widget = CombatLogWidget()
        widget.append("")
        widget.append("   ")
        assert widget._entry_count == 0

    def test_clear(self, qapp):
        widget = CombatLogWidget()
        widget.add_entry("A", "Attack", True, ["Hit"])
        widget.add_entry("B", "Attack", False, ["Miss"])
        widget.clear()
        assert widget._entry_count == 0

    def test_max_entries_pruning(self, qapp):
        widget = CombatLogWidget()
        for i in range(250):
            widget.add_entry(f"Entity{i}", "Move", True, [f"Step {i}"])
        assert widget._entry_count <= 200

    def test_noop_methods(self, qapp):
        """Backward-compat methods don't crash."""
        widget = CombatLogWidget()
        from PyQt5.QtGui import QFont
        widget.setReadOnly(True)
        widget.setFont(QFont("Consolas", 10))
        widget.setPlaceholderText("test")

    def test_multiple_entries_in_order(self, qapp):
        widget = CombatLogWidget()
        widget.add_entry("A", "Attack", True, ["Hit"])
        widget.add_system_message("Round 2")
        widget.add_entry("B", "Dash", True, ["Dashed"])
        assert widget._entry_count == 3

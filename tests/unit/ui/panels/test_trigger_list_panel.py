"""Tests for TriggerListPanel card display."""

import pytest
from unittest.mock import MagicMock
from ui.panels.trigger_list_panel import TriggerListPanel, TriggerCard, _format_condition, _format_reaction


class FakeTrigger:
    def __init__(self, event_type="ENTER_TILE", label="test_trigger", next_trigger=None):
        self.event_type = event_type
        self.label = label
        self.condition = MagicMock()
        self.condition.__class__ = type("AlwaysTrue", (), {})
        self.reaction = MagicMock()
        self.reaction.__class__ = type("AlertGamemaster", (), {})
        self.reaction.message = "Intruder detected!"
        self.next_trigger = next_trigger


class FakeTileData:
    def __init__(self, triggers=None):
        self.triggers = triggers or []


class TestTriggerListPanel:

    def test_creates(self, qapp):
        panel = TriggerListPanel()
        assert panel is not None

    def test_empty_shows_message(self, qapp):
        panel = TriggerListPanel()
        panel.set_tile(FakeTileData())
        assert not panel._empty_label.isHidden()

    def test_triggers_show_cards(self, qapp):
        triggers = [FakeTrigger(), FakeTrigger(event_type="ON_DAMAGE")]
        panel = TriggerListPanel()
        panel.set_tile(FakeTileData(triggers=triggers))
        assert len(panel._cards) == 2
        assert not panel._empty_label.isVisible()

    def test_add_signal(self, qapp):
        panel = TriggerListPanel()
        signals = []
        panel.trigger_added.connect(lambda: signals.append(True))
        # Find add button
        from PyQt5.QtWidgets import QPushButton
        for child in panel.findChildren(QPushButton):
            if "Add" in child.text():
                child.click()
                break
        assert len(signals) == 1

    def test_graph_view_signal(self, qapp):
        panel = TriggerListPanel()
        signals = []
        panel.graph_view_requested.connect(lambda: signals.append(True))
        from PyQt5.QtWidgets import QPushButton
        for child in panel.findChildren(QPushButton):
            if "Graph" in child.text():
                child.click()
                break
        assert len(signals) == 1


class TestTriggerCard:

    def test_shows_event_type(self, qapp):
        card = TriggerCard(FakeTrigger(event_type="ON_DAMAGE"))
        from PyQt5.QtWidgets import QLabel
        labels = [l.text() for l in card.findChildren(QLabel)]
        assert any("ON_DAMAGE" in l for l in labels)

    def test_edit_signal(self, qapp):
        signals = []
        card = TriggerCard(FakeTrigger(label="my_trigger"))
        card.edit_requested.connect(lambda l: signals.append(l))
        from PyQt5.QtWidgets import QPushButton
        for btn in card.findChildren(QPushButton):
            if btn.text() == "Edit":
                btn.click()
                break
        assert signals == ["my_trigger"]

    def test_delete_signal(self, qapp):
        signals = []
        card = TriggerCard(FakeTrigger(label="my_trigger"))
        card.delete_requested.connect(lambda l: signals.append(l))
        from PyQt5.QtWidgets import QPushButton
        for btn in card.findChildren(QPushButton):
            if btn.text() == "×":
                btn.click()
                break
        assert signals == ["my_trigger"]


class TestFormatters:

    def test_format_condition_always_true(self):
        cond = type("AlwaysTrue", (), {})()
        assert _format_condition(cond) == "Always fires"

    def test_format_reaction_alert(self):
        react = type("AlertGamemaster", (), {"message": "Help!"})()
        result = _format_reaction(react)
        assert "Alert GM" in result
        assert "Help!" in result

    def test_format_reaction_damage(self):
        react = type("ApplyDamage", (), {"damage_type": "fire", "amount": 5})()
        result = _format_reaction(react)
        assert "5" in result
        assert "fire" in result

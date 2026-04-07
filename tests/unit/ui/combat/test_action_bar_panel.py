"""Tests for ActionBarPanel."""

import pytest
from PyQt5.QtWidgets import QPushButton
from ui.combat.action_bar_panel import ActionBarPanel


@pytest.fixture
def panel(qapp):
    return ActionBarPanel(role="player")


class TestActionBarPanel:

    def test_creates_without_error(self, panel):
        assert panel is not None

    def test_has_action_buttons(self, panel):
        assert "attack" in panel._action_btns
        assert "dash" in panel._action_btns
        assert "dodge" in panel._action_btns

    def test_controls_disabled_when_not_turn(self, panel):
        panel.set_your_turn(False, "Goblin")
        for btn in panel._action_btns.values():
            assert not btn.isEnabled()
        assert not panel._end_turn_btn.isEnabled()

    def test_controls_enabled_when_turn(self, panel):
        panel.set_your_turn(True)
        for btn in panel._action_btns.values():
            assert btn.isEnabled()
        assert panel._end_turn_btn.isEnabled()

    def test_action_selected_signal(self, panel):
        panel.set_your_turn(True)
        signals = []
        panel.action_selected.connect(lambda aid: signals.append(aid))
        panel._action_btns["attack"].click()
        assert signals == ["attack"]

    def test_dash_signal(self, panel):
        panel.set_your_turn(True)
        signals = []
        panel.action_selected.connect(lambda aid: signals.append(aid))
        panel._action_btns["dash"].click()
        assert signals == ["dash"]

    def test_end_turn_signal(self, panel):
        panel.set_your_turn(True)
        signals = []
        panel.end_turn_requested.connect(lambda: signals.append(True))
        panel._end_turn_btn.click()
        assert len(signals) == 1

    def test_movement_display(self, panel):
        panel.update_from_hud({
            "movement_remaining": 25,
            "movement_max": 30,
            "actions": [],
            "bonus_actions": [],
            "reaction_available": True,
        })
        assert "25/30" in panel._move_label.text()

    def test_waiting_message(self, panel):
        panel.set_your_turn(False, "Goblin")
        assert panel._waiting_label.isVisibleTo(panel)
        assert "Goblin" in panel._waiting_label.text()

    def test_action_disabled_after_use(self, panel):
        panel.set_your_turn(True)
        panel.update_from_hud({
            "movement_remaining": 30,
            "movement_max": 30,
            "actions": [],  # No actions available (all used)
            "bonus_actions": [],
            "reaction_available": False,
        })
        assert not panel._action_btns["attack"].isEnabled()

"""Tests for NpcInteractionPanel."""

import pytest
from ui.exploration.npc_interaction_panel import NpcInteractionPanel


class TestNpcInteractionPanel:

    def test_creates(self, qapp):
        panel = NpcInteractionPanel()
        assert panel is not None
        assert panel.isHidden()

    def test_show_for_entity(self, qapp):
        panel = NpcInteractionPanel()
        panel.show_for_entity("Marta", [
            {"id": "talk", "label": "Talk", "enabled": True, "reason": ""},
            {"id": "inspect", "label": "Inspect", "enabled": True, "reason": ""},
        ])
        assert panel.isVisible()

    def test_interaction_signal(self, qapp):
        panel = NpcInteractionPanel()
        signals = []
        panel.interaction_chosen.connect(lambda name, iid: signals.append((name, iid)))
        panel.show_for_entity("Guard", [
            {"id": "talk", "label": "Talk", "enabled": True, "reason": ""},
        ])
        # Find and click the Talk button
        from PyQt5.QtWidgets import QPushButton
        for child in panel.findChildren(QPushButton):
            if child.text() == "Talk":
                child.click()
                break
        assert len(signals) == 1
        assert signals[0] == ("Guard", "talk")

    def test_dismiss_signal(self, qapp):
        panel = NpcInteractionPanel()
        signals = []
        panel.dismissed.connect(lambda: signals.append(True))
        panel.show_for_entity("Test", [{"id": "inspect", "label": "Inspect", "enabled": True}])
        panel.hide_panel()
        assert len(signals) == 1
        assert panel.isHidden()

    def test_disabled_button(self, qapp):
        panel = NpcInteractionPanel()
        panel.show_for_entity("Dead NPC", [
            {"id": "talk", "label": "Talk", "enabled": False, "reason": "Unconscious"},
        ])
        from PyQt5.QtWidgets import QPushButton
        for child in panel.findChildren(QPushButton):
            if child.text() == "Talk":
                assert not child.isEnabled()

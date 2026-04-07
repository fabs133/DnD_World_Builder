"""Tests for SessionPanel entity claim UI."""

import pytest
from PyQt5.QtWidgets import QApplication
from network.ui.session_panel import SessionPanel


class TestSessionPanelEntityClaim:

    def test_set_available_entities_dict(self):
        """set_available_entities populates combo from dict list."""
        panel = SessionPanel()
        panel.set_available_entities([
            {"name": "Hero", "entity_type": "player"},
            {"name": "Goblin", "entity_type": "enemy"},
        ])

        assert panel._entity_combo.count() == 2
        assert panel._entity_combo.itemText(0) == "Hero"
        assert panel._entity_combo.itemText(1) == "Goblin"

    def test_set_available_entities_strings(self):
        """set_available_entities works with plain string list."""
        panel = SessionPanel()
        panel.set_available_entities(["Hero", "Goblin"])

        assert panel._entity_combo.count() == 2
        assert panel._entity_combo.itemText(0) == "Hero"

    def test_set_available_entities_replaces(self):
        """Calling set_available_entities again replaces the old items."""
        panel = SessionPanel()
        panel.set_available_entities(["Hero"])
        panel.set_available_entities(["Rogue", "Mage"])

        assert panel._entity_combo.count() == 2
        assert panel._entity_combo.itemText(0) == "Rogue"

    def test_entity_claim_signal(self):
        """Clicking Claim emits entity_claim_requested with current text."""
        panel = SessionPanel()
        panel.set_available_entities(["Hero", "Goblin"])
        panel._entity_combo.setCurrentIndex(0)

        claimed = []
        panel.entity_claim_requested.connect(lambda name: claimed.append(name))
        panel._on_claim_clicked()

        assert len(claimed) == 1
        assert claimed[0] == "Hero"

    def test_entity_claim_empty_no_signal(self):
        """Clicking Claim with no selection does not emit."""
        panel = SessionPanel()
        # No entities loaded, combo is empty

        claimed = []
        panel.entity_claim_requested.connect(lambda name: claimed.append(name))
        panel._on_claim_clicked()

        assert len(claimed) == 0

    def test_clear_resets_entity_combo(self):
        """clear() empties the entity combo."""
        panel = SessionPanel()
        panel.set_available_entities(["Hero", "Goblin"])
        panel.clear()

        assert panel._entity_combo.count() == 0

    def test_chat_submitted_signal(self):
        """Chat input emits chat_submitted signal."""
        panel = SessionPanel()
        panel._chat_input.setText("Hello!")

        messages = []
        panel.chat_submitted.connect(lambda text: messages.append(text))
        panel._send_chat()

        assert len(messages) == 1
        assert messages[0] == "Hello!"
        assert panel._chat_input.text() == ""

    def test_chat_empty_not_submitted(self):
        """Empty chat input does not emit signal."""
        panel = SessionPanel()
        panel._chat_input.setText("   ")

        messages = []
        panel.chat_submitted.connect(lambda text: messages.append(text))
        panel._send_chat()

        assert len(messages) == 0

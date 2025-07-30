import pytest
from PyQt5.QtWidgets import QLineEdit, QTextEdit, QComboBox
from models.entities.game_entity import GameEntity
from ui.dialogs.entity_preview_dialog import EntityPreviewDialog

class DummyEntity(GameEntity):
    def __init__(self, name, etype, stats, inventory):
        super().__init__(name, etype, stats=stats, inventory=inventory)

@pytest.fixture
def qdlg(qapp):
    # Prepare a dummy entity with some stats and inventory
    ent = DummyEntity(
        name="Gob",
        etype="enemy",
        stats={"hp": 10, "speed": 30},
        inventory=["Slash", "Bite"]
    )
    dlg = EntityPreviewDialog(ent)
    return dlg, ent

def test_initial_fields(qdlg):
    dlg, ent = qdlg
    # Name field
    name_widget: QLineEdit = dlg.name_input
    assert name_widget.text() == ent.name
    # Type combo
    type_widget: QComboBox = dlg.type_input
    assert type_widget.currentText() == ent.entity_type
    # Stats fields
    assert "hp" in dlg.stat_inputs
    assert dlg.stat_inputs["hp"].text() == str(ent.stats["hp"])
    assert dlg.stat_inputs["speed"].text() == str(ent.stats["speed"])
    # Abilities box: both inventory items should appear in the text
    abilities: QTextEdit = dlg.abilities_box
    text = abilities.toPlainText()
    for item in ent.inventory:
        assert item in text

def test_get_entity_after_edit(qdlg):
    dlg, ent = qdlg
    # Change name
    dlg.name_input.setText("Orc")
    # Change type
    dlg.type_input.setCurrentText("npc")
    # Change stats: hp → 42, speed → 12.5
    dlg.stat_inputs["hp"].setText("42")
    dlg.stat_inputs["speed"].setText("12.5")
    # Change abilities
    dlg.abilities_box.setPlainText("Stomp\nRoar")
    # Retrieve updated entity
    new_ent = dlg.get_entity()
    assert isinstance(new_ent, GameEntity)
    assert new_ent.name == "Orc"
    assert new_ent.entity_type == "npc"
    # _safe_cast should convert "42"→int, "12.5"→float
    assert new_ent.stats["hp"] == 42 and isinstance(new_ent.stats["hp"], int)
    assert new_ent.stats["speed"] == 12.5 and isinstance(new_ent.stats["speed"], float)
    # Inventory lines
    assert new_ent.inventory == ["Stomp", "Roar"]

def test_safe_cast_non_numeric(qdlg):
    dlg, _ = qdlg
    # Access the protected helper
    assert dlg._safe_cast("123") == 123
    assert dlg._safe_cast("3.14") == 3.14
    assert dlg._safe_cast("foo") == "foo"

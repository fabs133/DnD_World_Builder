# tests/unit/core/characterCreation/test_character_gui.py

import json
import pytest
from PyQt5.QtWidgets import QInputDialog, QApplication
from core.characterCreation.character_gui import CharacterCreationWindow


# ------------------------------------------------------------
# DummyAPI for all tests
# ------------------------------------------------------------
class DummyAPI:
    def get(self, path):
        if path == "languages":
            return [{'name': 'Common'}]
        if path == "classes":
            return [{'name': 'Fighter'}, {'name': 'Cleric'}]
        if path == "races":
            return [{'name': 'Human'}]
        if path == "levels":
            return [
                {
                    "class": {"name": "Fighter"},
                    "features": [
                        {"name": "spell Strike"},
                        {"name": "spell Parry"}
                    ]
                }
            ]
        if path == "subclasses":
            return [
                {"name": "Life", "url": "/api/subclasses/life", "class": {"name": "Cleric"}},
                {"name": "Light", "url": "/api/subclasses/light", "class": {"name": "Cleric"}}
            ]
        return []
    
    def get_raw(self, path):
        if path.startswith("/api/races/"):
            return {"speed": 25, "ability_bonuses": [{"bonus": 2}]}
        return {}
    
    def list_categories(self):
        return ["languages", "classes", "races", "levels", "subclasses"]


# ------------------------------------------------------------
# General PyQt setup
# ------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def app():
    qapp = QApplication.instance() or QApplication([])
    yield qapp


# ------------------------------------------------------------
# CharacterCreationWindow with DummyAPI
# ------------------------------------------------------------
@pytest.fixture
def window(qtbot, monkeypatch):
    monkeypatch.setattr(QInputDialog, 'getText', lambda *args, **kwargs: ("filename", True))
    wnd = CharacterCreationWindow(api=DummyAPI())
    qtbot.addWidget(wnd)
    return wnd


# ------------------------------------------------------------
# Tests
# ------------------------------------------------------------
def test_collect_data_and_export(tmp_path, window, capsys, monkeypatch):
    window.name_input.setText("Hero")
    window.appearance_input.setPlainText("Tall")
    window.backstory_input.setPlainText("Brave knight")
    window.personality_input.setText("Bold")
    window.languages_input.setCurrentIndex(0)
    window.race_input.setCurrentIndex(0)
    window.char_class_input.setCurrentIndex(0)
    window.subclass_input.addItem("Champion")
    window.saving_throws_input.setText("STR")
    window.skills_input.setText("Athletics")
    
    # New stat input system using QSpinBox per stat
    window.stats_inputs['STR'].setValue(12)
    window.stats_inputs['DEX'].setValue(14)
    window.stats_inputs['CON'].setValue(11)
    window.stats_inputs['INT'].setValue(10)
    window.stats_inputs['WIS'].setValue(12)
    window.stats_inputs['CHA'].setValue(8)

    window.armor_class_input.setValue(18)
    window.speed_label.setText("32")
    window.initiative_input.setValue(4)
    window.conditions_input.setText("None")
    window.temporary_hp_input.setValue(0)
    window.inventory_list.addItem("Sword")
    window.currency_input.setText("10gp")
    window.passive_perception_label.setText("12")
    window.spells_input.clear()
    window.spells_input.addItem("Smite")
    window.spellslots_input.setValue(2)
    window.spellcasting_ability_label.setText("STR")

    out_file = tmp_path / "hero_export"
    monkeypatch.setattr(CharacterCreationWindow, 'get_file_name', lambda self: str(out_file))

    window.export_data()
    out = capsys.readouterr().out
    assert "Data exported successfully" in out

    data = json.loads((tmp_path / "hero_export.json").read_text())
    assert data["name"] == "Hero"
    assert data["class"] == "Fighter"
    assert data["race"] == "Human"
    assert data["spells"] == ["Smite"]



def test_export_canceled(window, monkeypatch, tmp_path):
    monkeypatch.setattr(CharacterCreationWindow, 'get_file_name', lambda self: None)
    window.export_data()
    files = list(tmp_path.glob("*.json"))
    assert not files


@pytest.mark.parametrize("method,widget,expected", [
    ("load_languages", "languages_input", ["Common"]),
    ("load_races", "race_input", ["Human"]),
    ("load_classes", "char_class_input", ["Fighter", "Cleric"]),
])
def test_load_dropdowns(window, method, widget, expected):
    combo = getattr(window, widget)
    combo.clear()
    getattr(window, method)()
    items = [combo.itemText(i) for i in range(combo.count())]
    for e in expected:
        assert e in items


def test_update_spells(qtbot):
    dummy_api = DummyAPI()
    wnd = CharacterCreationWindow(api=dummy_api)
    qtbot.addWidget(wnd)

    wnd.char_class_input.clear()
    wnd.char_class_input.addItem("Fighter")
    wnd.char_class_input.setCurrentIndex(0)

    wnd.spells_input.clear()
    wnd.update_spells()
    spells = [wnd.spells_input.item(i).text() for i in range(wnd.spells_input.count())]
    print("[DEBUG - test_update_spells] Spells after update:", spells)

    assert wnd.spells_input.count() == 2
    assert set(spells) == {"spell Strike", "spell Parry"}


def test_load_speed(window):
    window.race_input.setCurrentIndex(0)
    window.speed_label.clear()
    window.load_speed()
    assert window.speed_label.text() == "27"  # 25 + 2 from bonus


def test_update_subclasses(window):
    window.char_class_input.clear()
    window.char_class_input.addItem("Cleric")
    window.char_class_input.setCurrentIndex(0)  # correct index after clear

    window.subclass_input.clear()
    window.update_subclasses()

    expected = {"Life", "Light"}
    items = {window.subclass_input.itemText(i) for i in range(window.subclass_input.count())}
    print("[DEBUG - test_update_subclasses] subclasses:", items)
    assert items == expected


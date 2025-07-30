import pytest
from PyQt5.QtWidgets import QListWidgetItem
from models.entities.game_entity import GameEntity

import ui.dialogs.entity_editor_dialog as ed_mod
from ui.dialogs.entity_editor_dialog import EntityEditorDialog

class DummyEntity(GameEntity):
    def __init__(self, name, etype):
        super().__init__(name, etype)
        self.name = name
        self.entity_type = etype

@pytest.fixture
def tile_data():
    # A minimal tile_data with an entities list
    class TD:
        def __init__(self, entities):
            self.entities = entities
        def add_entity(self, e):
            self.entities.append(e)
    return TD(entities=[])

@pytest.fixture
def dlg(qapp, tile_data):
    # Create the dialog with no initial entities
    w = EntityEditorDialog(tile_data)
    return w

def test_initial_list_empty(dlg):
    # Entity list should start empty
    assert dlg.entity_list.count() == 0

def test_add_and_remove_entity(monkeypatch, dlg, tile_data):
    # Define and inject FakeNewDialog before calling add_entity
    import sys, types
    added = DummyEntity("Goblin", "enemy")
    class FakeNewDialog:
        def exec_(self): return True
        def get_entity(self): return added
    fake_mod = types.SimpleNamespace(NewEntityDialog=FakeNewDialog)
    monkeypatch.setitem(sys.modules, 'ui.dialogs.new_entity_dialog', fake_mod)
    # Now call add_entity()
    dlg.add_entity()
    # Now tile_data.entities gets updated
    assert tile_data.entities == [added]
    # And list widget has one item
    assert dlg.entity_list.count() == 1
    assert dlg.entity_list.item(0).text() == "Goblin (enemy)"

    # Now remove it
    dlg.entity_list.setCurrentRow(0)
    dlg.remove_entity()
    assert tile_data.entities == []
    assert dlg.entity_list.count() == 0

def test_import_from_rulebook(monkeypatch, dlg, tile_data):
    # Stub UniversalSearchDialog
    monster = DummyEntity("Ogre", "enemy")
    class FakeSearch:
        def __init__(self, mode): 
            assert mode == "monster"
        def exec_(self): return True
        def get_selected_object(self): return monster
    monkeypatch.setattr(ed_mod, "UniversalSearchDialog", FakeSearch)

    # Click import
    dlg.import_from_rulebook()
    assert tile_data.entities == [monster]
    assert dlg.entity_list.count() == 1
    assert dlg.entity_list.item(0).text() == "Ogre (enemy)"

def test_edit_triggers_for_selected(monkeypatch, dlg, tile_data):
    # Prepare one entity
    ent = DummyEntity("NPC", "npc")
    tile_data.entities.append(ent)
    dlg.entity_list.addItem("NPC (npc)")
    dlg.entity_list.setCurrentRow(0)

    # Stub TriggerEditorDialog so we capture the passed entity
    seen = {}
    class FakeTriggerEditor:
        def __init__(self, passed):
            seen['entity'] = passed
        def exec_(self): pass
    monkeypatch.setattr(ed_mod, "TriggerEditorDialog", FakeTriggerEditor)

    dlg.edit_triggers_for_selected()
    assert seen['entity'] is ent

def test_remove_nothing_when_none_selected(dlg, tile_data):
    # Nothing selected
    tile_data.entities[:] = []
    dlg.entity_list.clear()
    dlg.remove_entity()  # should not error
    assert tile_data.entities == []

def test_add_entity_cancel(monkeypatch, dlg, tile_data):
    # Define FakeNewDialog returning False, then inject
    import sys, types
    class FakeNewDialog:
        def exec_(self): return False
    fake_mod_cancel = types.SimpleNamespace(NewEntityDialog=FakeNewDialog)
    monkeypatch.setitem(sys.modules, 'ui.dialogs.new_entity_dialog', fake_mod_cancel)
    dlg.add_entity()
    # No change
    assert tile_data.entities == []
    assert dlg.entity_list.count() == 0

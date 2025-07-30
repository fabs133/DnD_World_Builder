# tests/unit/ui/interactions/test_universal_search_dialog_interactions.py
import pytest
from PyQt5.QtCore    import Qt
from PyQt5.QtWidgets import QPushButton
from ui.dialogs.universal_search_dialog import UniversalSearchDialog
from models.entities.game_entity import GameEntity

@pytest.fixture
def search_dialog(qtbot, mocker):
    # Mock the RulebookImporter in the dialog's namespace
    importer = mocker.patch(
        'ui.dialogs.universal_search_dialog.RulebookImporter'
    ).return_value
    importer.search_monsters.return_value = ['Goblin', 'Orc', 'Dragon']
    importer.search_spells.return_value   = ['Magic Missile', 'Shield']

    # Prepare EntityPreviewDialog to auto-accept
    preview_cls = mocker.patch(
        'ui.dialogs.universal_search_dialog.EntityPreviewDialog',
        autospec=True
    )
    preview_inst = preview_cls.return_value
    preview_inst.exec_.return_value = True
    fake_entity = GameEntity('Goblin', 'enemy')
    preview_inst.get_entity.return_value = fake_entity

    # importer.import_monster should return an object with to_game_entity()
    rb_obj = mocker.Mock()
    rb_obj.to_game_entity.return_value = fake_entity
    importer.import_monster.return_value = rb_obj

    dlg = UniversalSearchDialog(mode='monster')
    qtbot.addWidget(dlg)
    dlg.show()
    return dlg, importer, fake_entity


def test_initial_population(search_dialog):
    dlg, importer, _ = search_dialog
    count = dlg.result_list.count()
    assert count == 3
    names = {dlg.result_list.item(i).text() for i in range(count)}
    assert names == {'Goblin', 'Orc', 'Dragon'}


def test_filter_list(search_dialog, qtbot):
    dlg, _, _ = search_dialog
    dlg.search_input.setText('dr')
    visible = [
        dlg.result_list.item(i).text()
        for i in range(dlg.result_list.count())
        if not dlg.result_list.item(i).isHidden()
    ]
    assert visible == ['Dragon']


def test_category_switch(search_dialog):
    dlg, importer, _ = search_dialog
    dlg.category_selector.setCurrentText('Spell')
    count = dlg.result_list.count()
    assert count == 2
    spells = {dlg.result_list.item(i).text() for i in range(count)}
    assert spells == {'Magic Missile', 'Shield'}


def test_import_selected_success(search_dialog, qtbot):
    dlg, importer, fake_entity = search_dialog
    dlg.result_list.setCurrentRow(0)
    qtbot.mouseClick(dlg.import_btn, Qt.LeftButton)

    # After pressing import, the dialog should accept and set selected_object
    assert dlg.selected_object == fake_entity
    assert dlg.result() == dlg.Accepted


def test_import_selected_no_choice(search_dialog, qtbot, mocker):
    dlg, importer, _ = search_dialog
    dlg.result_list.setCurrentRow(-1)
    warning = mocker.patch('PyQt5.QtWidgets.QMessageBox.warning')
    qtbot.mouseClick(dlg.import_btn, Qt.LeftButton)
    warning.assert_called_once()

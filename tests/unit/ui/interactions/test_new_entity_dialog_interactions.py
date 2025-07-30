from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore    import Qt
import pytest

from ui.dialogs.new_entity_dialog import NewEntityDialog
from models.entities.game_entity import GameEntity
from core.gameCreation.trigger import Trigger
from models.flow.condition.condition_list import AlwaysTrue
from models.flow.reaction.reactions_list import AlertGamemaster

@pytest.fixture
def new_entity_dialog(qtbot, mocker):
    from core.gameCreation.trigger import Trigger
    from models.flow.condition.condition_list import AlwaysTrue
    from models.flow.reaction.reactions_list import AlertGamemaster

    # Build a dummy Trigger
    dummy = Trigger(
        event_type="ON_CREATE",
        condition=AlwaysTrue(),
        reaction=AlertGamemaster(""),
        label="sample_trigger"
    )

    # Patch the name *inside* the dialog module
    mocker.patch(
        "ui.dialogs.new_entity_dialog.trigger_presets",
        {"enemy": [dummy]}
    )

    dlg = NewEntityDialog()
    qtbot.addWidget(dlg)
    dlg.show()
    return dlg


def test_create_entity(new_entity_dialog, qtbot):
    dlg = new_entity_dialog

    # 1) Enter a name
    dlg.name_input.clear()
    qtbot.keyClicks(dlg.name_input, "Test Goblin")

    # 2) Select the type
    dlg.type_input.setCurrentText("enemy")

    # 3) Find the “Create Entity” button by its text
    buttons = dlg.findChildren(QPushButton)
    create_btn = next(btn for btn in buttons if btn.text() == "Create Entity")
    assert create_btn is not None

    # 4) Click it **after** filling in the form
    qtbot.mouseClick(create_btn, Qt.LeftButton)

    # 5) Verify the result
    created = dlg.get_entity()
    assert isinstance(created, GameEntity)
    assert created.name == "Test Goblin"
    # we patched trigger_presets so that "enemy" gives exactly one preset
    assert any(t.label == "sample_trigger" for t in created.triggers)


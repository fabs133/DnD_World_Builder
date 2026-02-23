"""Tests for UniversalSearchDialog: category switching, filtering, import flow."""

import pytest
from unittest.mock import MagicMock, patch

from PyQt5.QtWidgets import QDialog

from ui.dialogs.universal_search_dialog import UniversalSearchDialog


@pytest.fixture(autouse=True)
def stub_importer(monkeypatch):
    """Replace RulebookImporter so we don't need real data files."""
    fake = MagicMock()
    fake.search_monsters.return_value = ["Goblin", "Dragon", "Skeleton"]
    fake.search_spells.return_value = ["Fireball", "Heal"]
    fake.import_monster.return_value = MagicMock(
        to_game_entity=MagicMock(return_value=MagicMock(name="Goblin")),
    )
    fake.import_spell.return_value = MagicMock(
        to_game_entity=MagicMock(return_value=MagicMock(name="Fireball")),
    )
    monkeypatch.setattr(
        "ui.dialogs.universal_search_dialog.RulebookImporter",
        lambda: fake,
    )
    return fake


class TestUniversalSearchDialogInit:

    def test_default_mode_is_monster(self, qapp):
        dlg = UniversalSearchDialog()
        assert dlg.mode == "monster"
        assert dlg.category_selector.currentText() == "Monster"

    def test_spell_mode(self, qapp):
        dlg = UniversalSearchDialog(mode="spell")
        assert dlg.mode == "spell"
        assert dlg.category_selector.currentText() == "Spell"

    def test_monster_results_loaded(self, qapp):
        dlg = UniversalSearchDialog()
        names = [dlg.result_list.item(i).text() for i in range(dlg.result_list.count())]
        assert "Dragon" in names
        assert "Goblin" in names
        assert "Skeleton" in names

    def test_spell_results_loaded(self, qapp):
        dlg = UniversalSearchDialog(mode="spell")
        names = [dlg.result_list.item(i).text() for i in range(dlg.result_list.count())]
        assert "Fireball" in names
        assert "Heal" in names


class TestCategorySwitching:

    def test_switch_to_spell(self, qapp):
        dlg = UniversalSearchDialog(mode="monster")
        dlg.category_selector.setCurrentText("Spell")
        assert dlg.mode == "spell"
        names = [dlg.result_list.item(i).text() for i in range(dlg.result_list.count())]
        assert "Fireball" in names
        assert "Dragon" not in names

    def test_switch_to_monster(self, qapp):
        dlg = UniversalSearchDialog(mode="spell")
        dlg.category_selector.setCurrentText("Monster")
        assert dlg.mode == "monster"


class TestFiltering:

    def test_filter_hides_non_matching(self, qapp):
        dlg = UniversalSearchDialog()
        dlg.search_input.setText("gob")
        visible = [
            dlg.result_list.item(i).text()
            for i in range(dlg.result_list.count())
            if not dlg.result_list.item(i).isHidden()
        ]
        assert visible == ["Goblin"]

    def test_clear_filter_shows_all(self, qapp):
        dlg = UniversalSearchDialog()
        dlg.search_input.setText("gob")
        dlg.search_input.setText("")
        hidden = sum(
            1
            for i in range(dlg.result_list.count())
            if dlg.result_list.item(i).isHidden()
        )
        assert hidden == 0


class TestImport:

    def test_import_no_selection_shows_warning(self, qapp, monkeypatch):
        dlg = UniversalSearchDialog()
        dlg.result_list.clearSelection()
        dlg.result_list.setCurrentRow(-1)
        warned = []
        monkeypatch.setattr(
            "ui.dialogs.universal_search_dialog.QMessageBox.warning",
            lambda *a, **k: warned.append(True),
        )
        dlg.import_selected()
        assert warned

    def test_import_failed_shows_critical(self, qapp, stub_importer, monkeypatch):
        stub_importer.import_monster.return_value = None
        dlg = UniversalSearchDialog()
        dlg.result_list.setCurrentRow(0)
        crits = []
        monkeypatch.setattr(
            "ui.dialogs.universal_search_dialog.QMessageBox.critical",
            lambda *a, **k: crits.append(True),
        )
        dlg.import_selected()
        assert crits

    def test_import_success_accepts(self, qapp, monkeypatch):
        dlg = UniversalSearchDialog()
        dlg.result_list.setCurrentRow(0)
        # Stub the preview dialog to auto-accept
        fake_preview_cls = MagicMock()
        fake_preview_inst = fake_preview_cls.return_value
        fake_preview_inst.exec_.return_value = True
        fake_preview_inst.get_entity.return_value = MagicMock(name="Goblin")
        monkeypatch.setattr(
            "ui.dialogs.universal_search_dialog.EntityPreviewDialog",
            fake_preview_cls,
        )
        accepted = []
        monkeypatch.setattr(QDialog, "accept", lambda self: accepted.append(True))
        dlg.import_selected()
        assert accepted
        assert dlg.get_selected_object() is not None

    def test_get_selected_object_default_none(self, qapp):
        dlg = UniversalSearchDialog()
        assert dlg.get_selected_object() is None

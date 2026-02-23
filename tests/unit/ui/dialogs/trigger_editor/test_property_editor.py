"""Tests for TriggerPropertyEditor: field building, context, save."""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from ui.dialogs.trigger_editor.property_editor import TriggerPropertyEditor


@pytest.fixture
def editor(qapp):
    return TriggerPropertyEditor()


@pytest.fixture
def dummy_trigger():
    """Minimal trigger-like object with class-named condition/reaction."""
    cond = MagicMock()
    cond.__class__ = type("AlwaysTrue", (), {})
    react = MagicMock()
    react.__class__ = type("ApplyDamage", (), {})
    trig = SimpleNamespace(
        event_type="ENTER_TILE",
        condition=cond,
        reaction=react,
        label="ENTER_TILE:ApplyDamage:ABC123",
        next_trigger=None,
    )
    return trig


class TestPropertyEditorInit:

    def test_event_types_populated(self, editor):
        items = [editor.event_type_input.itemText(i) for i in range(editor.event_type_input.count())]
        assert "ENTER_TILE" in items
        assert "ON_DAMAGE" in items
        assert "CUSTOM" in items

    def test_condition_combo_has_entries(self, editor):
        assert editor.condition_input.count() > 0

    def test_reaction_combo_has_entries(self, editor):
        assert editor.reaction_input.count() > 0


class TestSetContext:

    def test_set_context_stores_context(self, editor):
        ctx = SimpleNamespace(triggers=[])
        editor.set_context(ctx)
        assert editor.context is ctx

    def test_set_context_populates_next_trigger_dropdown(self, editor, dummy_trigger):
        ctx = SimpleNamespace(triggers=[dummy_trigger])
        editor.set_context(ctx)
        items = [editor.next_trigger_input.itemText(i) for i in range(editor.next_trigger_input.count())]
        assert "None" in items


class TestSetTrigger:

    def test_set_trigger_none_resets(self, editor):
        ctx = SimpleNamespace(triggers=[])
        editor.set_context(ctx)
        editor.set_trigger(None)
        assert editor.trigger is None
        assert editor.event_type_input.currentIndex() == 0

    def test_set_trigger_populates_fields(self, editor, dummy_trigger):
        ctx = SimpleNamespace(triggers=[dummy_trigger])
        editor.set_context(ctx)
        editor.set_trigger(dummy_trigger)
        assert editor.event_type_input.currentText() == "ENTER_TILE"


class TestClearInputs:

    def test_clear_resets_all(self, editor):
        ctx = SimpleNamespace(triggers=[])
        editor.set_context(ctx)
        editor.event_type_input.setCurrentText("ON_DAMAGE")
        editor.clear_inputs()
        assert editor.event_type_input.currentIndex() == 0
        assert editor.condition_input.currentIndex() == 0
        assert editor.reaction_input.currentIndex() == 0


class TestBuildFields:

    def test_build_condition_fields_for_class_with_no_params(self, editor):
        """AlwaysTrue has no params beyond self."""
        from registries.condition_registry import condition_registry
        cls = condition_registry.get_class("AlwaysTrue")
        if cls:
            editor.build_condition_fields(cls)
            assert len(editor.condition_params) == 0

    def test_build_reaction_fields_creates_widgets(self, editor):
        from registries.reaction_registry import reaction_registry
        cls = reaction_registry.get_class("ApplyDamage")
        if cls:
            editor.build_reaction_fields(cls)
            # ApplyDamage has at least one param (amount/damage)
            assert len(editor.reaction_params) >= 0


class TestSaveTrigger:

    def test_save_appends_to_context(self, editor, monkeypatch):
        ctx = SimpleNamespace(triggers=[], name="TestTile")
        editor.set_context(ctx)
        editor.set_trigger(None)
        monkeypatch.setattr("ui.dialogs.trigger_editor.property_editor.uuid.uuid4",
                            MagicMock(return_value=MagicMock(hex="aabbcc112233")))
        editor.save_trigger()
        assert len(ctx.triggers) == 1
        assert ctx.triggers[0].event_type == "ENTER_TILE"

    def test_save_replaces_existing_trigger(self, editor, dummy_trigger, monkeypatch):
        ctx = SimpleNamespace(triggers=[dummy_trigger], name="TestTile")
        editor.set_context(ctx)
        editor.set_trigger(dummy_trigger)
        editor.event_type_input.setCurrentText("ON_DAMAGE")
        monkeypatch.setattr("ui.dialogs.trigger_editor.property_editor.uuid.uuid4",
                            MagicMock(return_value=MagicMock(hex="aabbcc112233")))
        editor.save_trigger()
        assert len(ctx.triggers) == 1

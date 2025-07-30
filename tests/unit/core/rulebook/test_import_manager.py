# tests/unit/core/rulebook/test_import_manager.py
import pytest
from core.rulebook.import_manager import RulebookImporter
from models.entities.game_entity import GameEntity
from models.spell import Spell

class DummyEntityWrapper:
    def to_game_entity(self):
        # Return a minimal GameEntity so isinstance checks pass
        return GameEntity(name="DummyMon", entity_type="npc")

class DummySpellWrapper:
    def __init__(self, name):
        self.name = name

    def to_spell(self):
        # Supply all required positional/keyword args
        return Spell(
            self.name,
            interrupt_difficulty=0,
            cast_priority="normal",
            level=1,
            school="Evocation",
            casting_time="1 action",
            range="60 feet",
            components=["V","S"],
            duration="Instantaneous",
            description="Dummy spell",
            damage={"type": "force", "amount": 5},
            effect={"type": "buff", "details": "Dummy"},
            reaction_mode="after"
        )


@pytest.fixture
def importer(monkeypatch):
    rbi = RulebookImporter()
    # Stub out list_all for both monsters and spells
    monkeypatch.setattr(rbi.monsters, "list_all", lambda: [{"name":"Goblin"}])
    monkeypatch.setattr(rbi.spells, "list_all", lambda: [{"name":"Magic Missile"}])

    # Stub out get_by_name
    monkeypatch.setattr(rbi.monsters, "get_by_name",
                        lambda name: DummyEntityWrapper() if name=="Goblin" else None)
    monkeypatch.setattr(rbi.spells, "get_by_name",
                    lambda name: DummySpellWrapper(name) if name == "Magic Missile" else None)

    return rbi

def test_search_monsters_empty(monkeypatch):
    rbi = RulebookImporter()
    monkeypatch.setattr(rbi.monsters, "list_all", lambda: None)
    assert rbi.search_monsters() == []

def test_search_spells_empty(monkeypatch):
    rbi = RulebookImporter()
    monkeypatch.setattr(rbi.spells, "list_all", lambda: {})
    assert rbi.search_spells() == []

def test_search_monsters(importer):
    assert importer.search_monsters() == ["Goblin"]

def test_search_spells(importer):
    assert importer.search_spells() == ["Magic Missile"]

def test_import_monster_success(importer):
    ge = importer.import_monster("Goblin")
    assert isinstance(ge, GameEntity)
    assert ge.name == "DummyMon"

def test_import_monster_not_found(importer):
    assert importer.import_monster("Orc") is None

def test_import_spell_success(importer):
    sp = importer.import_spell("Magic Missile")
    assert isinstance(sp, Spell)
    assert sp.name == "Magic Missile"

def test_import_spell_not_found(importer):
    assert importer.import_spell("Fireball") is None

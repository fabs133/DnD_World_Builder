import sqlite3
import json
import pytest

import models.entities.character as char_mod
from models.entities.character import Character

@pytest.fixture
def db_conn(tmp_path):
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            character_id INTEGER PRIMARY KEY,
            name TEXT,
            class TEXT,
            level INTEGER,
            hp INTEGER,
            stats TEXT,
            inventory TEXT,
            spells TEXT
        )
    ''')
    conn.commit()
    return conn

def make_minimal_char(**overrides):
    dummy_spell = {
        "name": "MagicMissile",
        "level": 1,
        "school": "Evocation",
        "casting_time": "1 action",
        "range": "120 ft",
        "components": [],
        "duration": "Instantaneous",
        "description": "Creates darts"
    }
    defaults = {
        "name": "Test",
        "appearance": "",
        "backstory": "",
        "personality": "",
        "languages": [],
        "spellslots": {},
        "spellcasting_ability": {},
        "char_class": "Wizard",
        "char_class_features": {},
        "species": "Human",
        "species_traits": {},
        "subclass": None,
        "feats": [],
        "background": "",
        "level": 5,
        "xp": 100,
        "armor_class": 15,
        "death_saves": {},
        "hp": 30,
        "stats": {"max_hp": 30, "str": 10},
        "inventory": ["sword", "shield"],
        "training_proficiencies": {},
        "spells": [dummy_spell],
        "proficiency_bonus": 3,
        "hit_dice": {},
        "saving_throws": {},
        "skills": {},
        "temporary_hp": 0,
        "inspiration": False,
        "passive_perception": 10,
        "conditions": [],
        "currency": {},
        "exhaustion_level": 0,
        "armor": [],
        "weapons": [],
        "speed": 30,
        "initiative": 2,
        "resistances": [],
        "immunities": [],
        "vulnerabilities": []
    }
    defaults.update(overrides)
    return Character(**defaults)

def test_take_damage_and_heal():
    stats = {"max_hp": 50, "str": 10}
    char = make_minimal_char(hp=20, stats=stats)
    char.take_damage(5)
    assert char.hp == 15
    char.take_damage(100)
    assert char.hp == 0

    char.heal(10)
    assert char.hp == 10
    char.heal(100)
    assert char.hp == stats["max_hp"]

def test_cast_spell_does_not_error_and_uses_dummy(monkeypatch):
    created = {"inst": False}
    class DummySpell:
        def __init__(self, **kwargs):
            created["inst"] = True
        def cast(self, caster, target):
            pass

    monkeypatch.setattr(char_mod, "Spell", DummySpell)

    char = make_minimal_char()
    char.cast_spell("MagicMissile", target=None)

    assert created["inst"] is True

def test_save_to_db_inserts_row(db_conn):
    char = make_minimal_char()
    char.save_to_db(db_conn)

    cursor = db_conn.cursor()
    cursor.execute('SELECT name, class, level, hp, stats, inventory, spells FROM characters')
    row = cursor.fetchone()

    assert row[0] == "Test"
    assert row[1] == "Wizard"
    assert row[2] == 5
    assert row[3] == 30

    stats_loaded = json.loads(row[4])
    assert stats_loaded == {"max_hp": 30, "str": 10}

    inv_loaded = json.loads(row[5])
    assert inv_loaded == ["sword", "shield"]

    spells_loaded = json.loads(row[6])
    assert isinstance(spells_loaded, list)
    assert spells_loaded[0]["name"] == "MagicMissile"

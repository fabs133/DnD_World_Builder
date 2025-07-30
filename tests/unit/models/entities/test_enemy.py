import sqlite3
import json
import pytest

import models.entities.enemy as enemy_mod
from models.entities.enemy import Enemy

@pytest.fixture
def db_conn(tmp_path):
    db_file = tmp_path / "test_enemies.db"
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    # create the enemies table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS enemies (
            enemy_id INTEGER PRIMARY KEY,
            name TEXT,
            hp INTEGER,
            stats TEXT,
            abilities TEXT
        )
    """)
    conn.commit()
    return conn

def make_minimal_enemy(**overrides):
    dummy_spell = {
        "name": "Sting",
        "level": 0,
        "school": "None",
        "casting_time": "1 action",
        "range": "Melee",
        "components": [],
        "duration": "Instant",
        "description": "Sting",
    }
    defaults = {
        "name": "Goblin",
        "armor_class": 15,
        "hp": 20,
        "stats": {"max_hp": 20, "str": 12},
        "saving_throws": {},
        "attacks": [{"name": "Slash", "damage": "1d6", "to_hit": 4}],
        "speed": 30,
        "resistances": [],
        "immunities": [],
        "vulnerabilities": [],
        "condition_immunities": [],
        "challenge_rating": 0.25,
        "xp": 50,
        "conditions": [],
        "initiative": 2,
        "spells": [dummy_spell],
    }
    defaults.update(overrides)
    return Enemy(**defaults)

def test_take_damage_and_heal():
    stats = {"max_hp": 50}
    e = make_minimal_enemy(hp=10, stats=stats)
    e.take_damage(3)
    assert e.hp == 7
    e.take_damage(20)
    assert e.hp == 0

    e.heal(5)
    assert e.hp == 5
    e.heal(100)
    assert e.hp == stats["max_hp"]

def test_cast_spell_invokes_spell_cast(monkeypatch):
    called = {}
    class DummySpell:
        def __init__(self, **kwargs):
            called["init"] = kwargs
        def cast(self, caster, target):
            called["cast"] = (caster, target)
        def __del__(self):
            called["deleted"] = True

    # Patch the Spell used in the Enemy module
    monkeypatch.setattr(enemy_mod, "Spell", DummySpell)

    e = make_minimal_enemy()
    target = object()
    # should not raise, and should call our dummy
    e.cast_spell("Sting", target)
    assert "init" in called
    assert called["cast"] == (e, target)

def test_save_to_db_inserts_row(db_conn):
    e = make_minimal_enemy()
    e.save_to_db(db_conn)

    cur = db_conn.cursor()
    cur.execute("SELECT name, hp, stats, abilities FROM enemies")
    row = cur.fetchone()
    assert row[0] == "Goblin"
    assert row[1] == 20

    stats_loaded = json.loads(row[2])
    assert stats_loaded == {"max_hp": 20, "str": 12}

    abilities_loaded = json.loads(row[3])
    assert abilities_loaded == [{"name": "Slash", "damage": "1d6", "to_hit": 4}]

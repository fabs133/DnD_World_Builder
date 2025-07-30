import sqlite3
import json
import pytest

import models.entities.named_enemy as ne_mod
from models.entities.named_enemy import NamedEnemy

@pytest.fixture
def db_conn(tmp_path):
    db_file = tmp_path / "test_named.db"
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
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

def make_named_enemy(**overrides):
    # one dummy spell dict
    dummy_spell = {
        "name": "Roar",
        "level": 0,
        "school": "None",
        "casting_time": "1 action",
        "range": "Self",
        "components": [],
        "duration": "Instant",
        "description": "Terrifying roar",
    }

    defaults = {
        "name": "Tarrasque",
        "armor_class": 25,
        "hp": 676,
        "stats": {"max_hp": 676, "str": 30},
        "saving_throws": {},
        "attacks": [{"name": "Bite", "damage": "2d6+10", "to_hit": 19}],
        "speed": 40,
        "resistances": [],
        "immunities": [],
        "vulnerabilities": [],
        "condition_immunities": [],
        "challenge_rating": 30.0,
        "xp": 155000,
        "conditions": [],
        "initiative": 1,
        "spells": [dummy_spell],
        "backstory": "World-ending beast",
        "legendary_actions": ["Swipe", "Stomp"],
        "lair_actions": ["Earthquake"],
        "regional_effects": ["Tremors"],
        "spellcasting_ability": {"spell_save_dc": 20, "spell_attack_bonus": 11},
        "phases": [{"hp_threshold": 338, "ability": "Enrage"}]
    }
    defaults.update(overrides)
    return NamedEnemy(**defaults)

def test_inheritance_and_attributes():
    ne = make_named_enemy()
    # Attributes from Enemy + NamedEnemy
    assert ne.name == "Tarrasque"
    assert ne.armor_class == 25
    assert ne.hp == 676
    assert ne.stats["str"] == 30

    # NamedEnemy-specific fields
    assert ne.backstory.startswith("World")
    assert "Swipe" in ne.legendary_actions
    assert ne.spellcasting_ability["spell_save_dc"] == 20
    assert isinstance(ne.phases, list)

def test_take_damage_and_heal():
    ne = make_named_enemy(hp=100, stats={"max_hp": 100})
    ne.take_damage(20)
    assert ne.hp == 80
    ne.take_damage(200)
    assert ne.hp == 0

    ne.heal(30)
    assert ne.hp == 30
    ne.heal(500)
    assert ne.hp == 100

def test_cast_spell_calls_cast_with_dummy(monkeypatch):
    called = {}
    class DummySpell:
        def __init__(self, **kwargs):
            called["init"] = kwargs
        def cast(self, caster, target):
            called["cast"] = (caster, target)
        def __del__(self):
            called["del"] = True

    monkeypatch.setattr(ne_mod, "Spell", DummySpell)

    ne = make_named_enemy()
    tgt = object()
    ne.cast_spell("Roar", tgt)

    assert "init" in called
    assert called["cast"] == (ne, tgt)

def test_save_to_db_inserts_row(db_conn):
    ne = make_named_enemy()
    ne.save_to_db(db_conn)

    cur = db_conn.cursor()
    cur.execute("SELECT name, hp, stats, abilities FROM enemies")
    row = cur.fetchone()
    assert row[0] == "Tarrasque"
    assert row[1] == 676

    stats_loaded = json.loads(row[2])
    assert stats_loaded == {"max_hp": 676, "str": 30}

    abilities_loaded = json.loads(row[3])
    assert isinstance(abilities_loaded, list)
    assert abilities_loaded[0]["name"] == "Bite"

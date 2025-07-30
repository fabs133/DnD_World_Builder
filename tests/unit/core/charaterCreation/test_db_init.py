# tests/unit/db/test_db_init.py
import sqlite3
from sqlite3 import Connection
import pytest
from core.characterCreation import db_init

@pytest.fixture(autouse=True)
def in_memory_db(monkeypatch):
    """Monkey‐patch sqlite3.connect so that any call uses an in‐memory DB."""
    orig_connect = sqlite3.connect
    monkeypatch.setattr(sqlite3, "connect", lambda path: orig_connect(":memory:"))
    yield
    # pytest will undo the patch for you

def test_initialize_db_returns_connection():
    conn = db_init.initialize_db()
    assert isinstance(conn, Connection)

def test_tables_created():
    conn = db_init.initialize_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    expected = {
        "characters", "enemies", "spells",
        "world_info", "combat_log", "damage_types"
    }
    assert expected.issubset(tables)

@pytest.mark.parametrize("table,cols", [
    ("characters",     ["character_id","name","class","level","hp","stats","inventory","spells"]),
    ("enemies",        ["enemy_id","name","hp","stats","abilities"]),
    ("spells",         ["spell_id","name","duration","damage","effect","range","area_of_effect"]),
    ("world_info",     ["world_id","description","map","time_of_day","weather_conditions"]),
    ("combat_log",     ["combat_id","turn_number","attacker_id","target_id","damage_dealt","spell_used","ability_used"]),
    ("damage_types",   ["damage_type_id","type_name","resistance_factor"]),
])
def test_table_schema(table, cols):
    conn = db_init.initialize_db()
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    actual = [row[1] for row in cur.fetchall()]
    assert actual == cols, f"{table} columns {actual} != expected {cols}"

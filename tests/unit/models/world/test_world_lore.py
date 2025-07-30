import sqlite3
import json
import pytest

from models.world.world_lore import WorldLore

@pytest.fixture
def db_conn(tmp_path):
    # Create an on‐disk SQLite DB so we can run initialize schema here
    db_file = tmp_path / "world.db"
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    # Create the world_info table expected by save_to_db()
    cur.execute("""
        CREATE TABLE world_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,
            map TEXT,
            time_of_day TEXT,
            weather_conditions TEXT
        )
    """)
    conn.commit()
    return conn

def test_constructor_and_describe_world():
    wl = WorldLore(
        description="Ancient Realm",
        map_data={"zones": ["forest", "dungeon"]},
        time_of_day="morning",
        weather_conditions="sunny"
    )
    # Attributes set correctly
    assert wl.description == "Ancient Realm"
    assert wl.map_data == {"zones": ["forest", "dungeon"]}
    assert wl.time_of_day == "morning"
    assert wl.weather_conditions == "sunny"

    # describe_world returns the formatted string
    desc = wl.describe_world()
    assert "Ancient Realm" in desc
    assert "Time: morning" in desc
    assert "Weather: sunny" in desc
    assert desc.startswith("World Description:")

def test_update_weather_prints_and_sets(capsys):
    wl = WorldLore("D", {}, "noon", "rainy")
    wl.update_weather("stormy")
    # Attribute updated
    assert wl.weather_conditions == "stormy"
    out = capsys.readouterr().out.strip()
    assert out == "Weather updated to: stormy"

def test_update_time_of_day_prints_and_sets(capsys):
    wl = WorldLore("Desc", {}, "night", "clear")
    wl.update_time_of_day("dawn")
    assert wl.time_of_day == "dawn"
    out = capsys.readouterr().out.strip()
    assert out == "Time of day updated to: dawn"

def test_save_to_db_inserts_row(db_conn):
    data = {"level":1, "area":"plains"}
    wl = WorldLore("Lore", data, "evening", "foggy")
    wl.save_to_db(db_conn)

    cur = db_conn.cursor()
    cur.execute("SELECT description, map, time_of_day, weather_conditions FROM world_info")
    row = cur.fetchone()
    # description matches
    assert row[0] == "Lore"
    # map column is JSON of our dict
    loaded_map = json.loads(row[1])
    assert loaded_map == data
    assert row[2] == "evening"
    assert row[3] == "foggy"

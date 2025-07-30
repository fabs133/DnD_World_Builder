import sqlite3
import random
import pytest

from models.entities.player import Player

# A minimal stand‐in for your Character
class DummyCharacter:
    def __init__(self, name, stats=None):
        self.name = name
        self.stats = stats or {}

    def cast_spell(self, spell_name, target):
        # record for the test
        self._last_cast = (spell_name, target)


@pytest.fixture
def db_conn(tmp_path):
    db_file = tmp_path / "test_player.db"
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    # players table for move()
    cur.execute("""
        CREATE TABLE players (
            player_id INTEGER PRIMARY KEY,
            x INTEGER,
            y INTEGER
        )
    """)
    # combat_log table for attack()
    cur.execute("""
        CREATE TABLE combat_log (
            log_id INTEGER PRIMARY KEY,
            turn_number INTEGER,
            attacker_id INTEGER,
            target_id INTEGER,
            damage_dealt INTEGER,
            spell_used TEXT,
            ability_used TEXT
        )
    """)
    conn.commit()
    return conn

@pytest.fixture
def dummy_character():
    # default STR=2, WIS=4
    return DummyCharacter("Hero", stats={"str": 2, "wis": 4})

@pytest.fixture
def player(db_conn, dummy_character):
    # insert a row so UPDATE in move() actually affects something
    cur = db_conn.cursor()
    cur.execute("INSERT INTO players (player_id, x, y) VALUES (?, ?, ?)", (1, 0, 0))
    db_conn.commit()
    return Player(dummy_character, db_conn, player_id=1)

def test_default_position(player):
    assert player.position == (0, 0)

@pytest.mark.parametrize("direction,expected", [
    ("north", (0, 1)),
    ("south", (0, -1)),
    ("east",  (1, 0)),
    ("west",  (-1, 0)),
    ("invalid", (0, 0)),
])
def test_move_updates_position_and_db(player, db_conn, direction, expected):
    new_pos = player.move(direction)
    # internal state
    assert player.position == expected
    assert new_pos == expected

    # persisted
    cur = db_conn.cursor()
    cur.execute("SELECT x, y FROM players WHERE player_id = ?", (1,))
    row = cur.fetchone()
    assert row == expected

def test_attack_hit_and_log(monkeypatch, player, db_conn):
    # Target with high AC to test miss/hit separately
    class DummyTarget:
        def __init__(self):
            self.character_id = 2
            self.hp = 10
        def take_damage(self, dmg):
            self.took = dmg
            self.hp -= dmg

    target = DummyTarget()

    # Force d20 roll = 18 so roll+str_mod(2)=20 ≥ ac(10)
    monkeypatch.setattr(random, "randint", lambda a, b: 18)

    # give target an armor_class for the test
    target.armor_class = 10

    hit, damage = player.attack(target)
    assert hit is True
    assert damage == 2         # str_mod == 2
    assert target.took == 2

    # check combat_log
    cur = db_conn.cursor()
    cur.execute("""
        SELECT attacker_id, target_id, damage_dealt, spell_used, ability_used
        FROM combat_log
    """)
    row = cur.fetchone()
    assert row == (1, 2, 2, None, None)

def test_attack_miss_and_log(monkeypatch, player, db_conn):
    class DummyTarget2:
        def __init__(self):
            self.player_id = 3
            self.hp = 10
        def take_damage(self, dmg):
            self.took = dmg
            self.hp -= dmg

    target = DummyTarget2()
    # Set AC high so any roll misses
    target.armor_class = 30

    # Force d20 roll = 1 → 1+2 < 30
    monkeypatch.setattr(random, "randint", lambda a, b: 1)

    hit, damage = player.attack(target)
    assert hit is False
    assert damage == 0
    assert not hasattr(target, "took")

    cur = db_conn.cursor()
    cur.execute("""
        SELECT attacker_id, target_id, damage_dealt
        FROM combat_log
    """)
    row = cur.fetchone()
    assert row == (1, 3, 0)

def test_cast_spell_delegates_to_character(player, dummy_character):
    target = object()
    # call through
    res = player.cast_spell("Fireball", target)
    assert dummy_character._last_cast == ("Fireball", target)
    # returns None (since Character.cast_spell doesn’t return)
    assert res is None

def test_investigate_roll(monkeypatch, player):
    # force roll of 10; wis_mod = 4 → total = 14
    monkeypatch.setattr(random, "randint", lambda a, b: 10)
    player.character.stats["wis"] = 4
    assert player.investigate("anywhere") == 14

def test_interact_with_and_without(player):
    class ObjWith:
        def __init__(self):
            self.hit = False
        def interact(self, ply):
            self.hit = True
            return "done"

    o = ObjWith()
    assert player.interact(o) == "done"
    assert o.hit is True

    class ObjWithout:
        pass

    assert player.interact(ObjWithout()) is None

def test_take_turn_raises(player):
    # take_turn is not implemented
    with pytest.raises(NotImplementedError) as ei:
        player.take_turn()
    assert "take_turn" in str(ei.value)

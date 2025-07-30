import sqlite3

def initialize_db():
    """
    Initializes the SQLite database for the DnD project by creating the necessary tables if they do not exist.

    The following tables are created:
    - characters: Stores character information such as name, class, level, HP, stats, inventory, and spells.
    - enemies: Stores enemy information including name, HP, stats, and abilities.
    - spells: Stores spell details such as name, duration, damage, effect, range, and area of effect.
    - world_info: Stores world-related information like description, map, time of day, and weather conditions.
    - combat_log: Stores combat log entries including turn number, attacker and target IDs, damage dealt, and used spells or abilities.
    - damage_types: Stores types of damage and their resistance factors.

    Returns
    -------
    sqlite3.Connection
        The connection object to the initialized SQLite database.
    """
    db_conn = sqlite3.connect('dnd_database.db')
    cursor = db_conn.cursor()

    # Create tables
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enemies (
            enemy_id INTEGER PRIMARY KEY,
            name TEXT,
            hp INTEGER,
            stats TEXT,
            abilities TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS spells (
            spell_id INTEGER PRIMARY KEY,
            name TEXT,
            duration INTEGER,
            damage INTEGER,
            effect TEXT,
            range INTEGER,
            area_of_effect TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS world_info (
            world_id INTEGER PRIMARY KEY,
            description TEXT,
            map TEXT,
            time_of_day TEXT,
            weather_conditions TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS combat_log (
            combat_id INTEGER PRIMARY KEY,
            turn_number INTEGER,
            attacker_id INTEGER,
            target_id INTEGER,
            damage_dealt INTEGER,
            spell_used TEXT,
            ability_used TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS damage_types (
            damage_type_id INTEGER PRIMARY KEY,
            type_name TEXT,
            resistance_factor REAL
        )
    ''')

    db_conn.commit()
    return db_conn

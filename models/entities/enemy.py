from models.entities.game_entity import GameEntity
from models.spell import Spell  
import json

class Enemy(GameEntity):
    """
    Represents an enemy entity in the game.

    :param name: Name of the enemy
    :type name: str
    :param armor_class: Armor class value
    :type armor_class: int
    :param hp: Hit points
    :type hp: int
    :param stats: Dictionary of stats (e.g., {"Strength": 10, ...})
    :type stats: dict
    :param saving_throws: Dictionary of saving throw values
    :type saving_throws: dict
    :param attacks: List of attack dictionaries
    :type attacks: list
    :param speed: Movement speed
    :type speed: int
    :param resistances: List of resistances
    :type resistances: list
    :param immunities: List of immunities
    :type immunities: list
    :param vulnerabilities: List of vulnerabilities
    :type vulnerabilities: list
    :param condition_immunities: List of condition immunities
    :type condition_immunities: list
    :param challenge_rating: Challenge rating
    :type challenge_rating: float
    :param xp: Experience points
    :type xp: int
    :param conditions: List of current conditions
    :type conditions: list
    :param initiative: Initiative value
    :type initiative: int
    :param spells: List of spells
    :type spells: list
    """
    def __init__(
        self, name, armor_class, hp, stats, saving_throws, attacks, speed,
        resistances, immunities, vulnerabilities, condition_immunities,
        challenge_rating, xp, conditions, initiative, spells
    ):
        """
        Initialize an Enemy instance.

        See class docstring for parameter details.
        """
        super().__init__(name, "enemy")
        self.name = name  # String
        self.armor_class = armor_class  # Integer
        self.hp = hp  # Integer
        self.stats = stats  # Dictionary: { "Strength": 10, "Dexterity": 12, ... }
        self.saving_throws = saving_throws  # Dictionary: { "Strength": 2, "Dexterity": 4, ...}
        self.attacks = attacks  # List of attack dictionaries: { "name": "Bite", "damage": "1d6+2 piercing", "to_hit": 4 }
        self.speed = speed  # Integer
        self.resistances = resistances  # List of strings (e.g., ["fire", "cold"])
        self.immunities = immunities  # List of strings (e.g., ["poison"])
        self.vulnerabilities = vulnerabilities  # List of strings (e.g., ["lightning"])
        self.condition_immunities = condition_immunities  # List of strings (e.g., ["Charmed", "Frightened"])
        self.challenge_rating = challenge_rating  # Float
        self.xp = xp  # Integer
        self.conditions = conditions  # List of strings
        self.initiative = initiative  # Integer
        self.spells = spells  # List of spells
        self.spell_details = {spell['name']: spell for spell in spells}  # Store detailed spell information

    def take_damage(self, damage):
        """
        Apply damage to the enemy, reducing its hit points.

        :param damage: Amount of damage to apply
        :type damage: int
        """
        self.hp = max(0, self.hp - damage)

    def heal(self, amount):
        """
        Heal the enemy by a specified amount, up to its maximum hit points.

        :param amount: Amount to heal
        :type amount: int
        """
        self.hp = min(self.hp + amount, self.stats['max_hp'])

    def cast_spell(self, spell_name, target):
        """
        Cast a spell.

        :param spell_name: Name of the spell to cast
        :type spell_name: str
        :param target: Target of the spell
        :type target: object
        """
        spell_data = self.spell_details.get(spell_name)
        if spell_data:
            spell = Spell(
                name=spell_data['name'],
                level=spell_data['level'],
                school=spell_data['school'],
                casting_time=spell_data['casting_time'],
                range=spell_data['range'],
                components=spell_data['components'],
                duration=spell_data['duration'],
                description=spell_data['description'],
                damage=spell_data.get('damage'),
                healing=spell_data.get('healing'),
                effect=spell_data.get('effect')
            )
            spell.cast(self, target)

    def save_to_db(self, db_conn):
        """
        Save the enemy to the database.

        :param db_conn: Database connection object
        :type db_conn: sqlite3.Connection
        """
        cursor = db_conn.cursor()
        cursor.execute('''
            INSERT INTO enemies (name, hp, stats, abilities)
            VALUES (?, ?, ?, ?)
        ''', (
            self.name,
            self.hp,
            json.dumps(self.stats),
            json.dumps(self.attacks)   # store attacks under the "abilities" column
        ))
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from models.entities.game_entity import GameEntity
from models.spell import Spell
import json


@dataclass
class Character(GameEntity):
    """
    Dataclass representing a player character.

    Inherits base entity behavior from GameEntity and adds
    all D&D 5e character sheet fields.
    """

    name: str = ""
    appearance: str = ""
    backstory: str = ""
    personality: str = ""
    languages: List[str] = field(default_factory=list)
    spellslots: Dict[str, Any] = field(default_factory=dict)
    spellcasting_ability: Dict[str, Any] = field(default_factory=dict)
    char_class: str = ""
    char_class_features: Dict[str, Any] = field(default_factory=dict)
    species: str = ""
    species_traits: Dict[str, Any] = field(default_factory=dict)
    subclass: str = ""
    feats: List[str] = field(default_factory=list)
    background: str = ""
    level: int = 1
    xp: int = 0
    armor_class: int = 10
    death_saves: Dict[str, Any] = field(default_factory=dict)
    hp: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    inventory: List[str] = field(default_factory=list)
    training_proficiencies: Dict[str, Any] = field(default_factory=dict)
    spells: List[Dict[str, Any]] = field(default_factory=list)
    proficiency_bonus: int = 2
    hit_dice: Dict[str, Any] = field(default_factory=dict)
    saving_throws: Dict[str, Any] = field(default_factory=dict)
    skills: Dict[str, Any] = field(default_factory=dict)
    temporary_hp: int = 0
    inspiration: bool = False
    passive_perception: int = 10
    conditions: List[str] = field(default_factory=list)
    currency: Dict[str, Any] = field(default_factory=dict)
    exhaustion_level: int = 0
    armor: List[str] = field(default_factory=list)
    weapons: List[str] = field(default_factory=list)
    speed: int = 30
    initiative: int = 0
    resistances: List[str] = field(default_factory=list)
    immunities: List[str] = field(default_factory=list)
    vulnerabilities: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize the GameEntity base class and derived fields."""
        super().__init__(self.name, "player", stats=self.stats, inventory=self.inventory)
        self.spell_details = {
            spell['name']: spell for spell in self.spells
            if isinstance(spell, dict) and 'name' in spell
        }

    def take_damage(self, damage):
        """
        Apply damage to the character.

        :param int damage: Amount of damage to apply
        """
        self.hp = max(0, self.hp - damage)

    def heal(self, amount):
        """
        Heal the character.

        :param int amount: Amount of healing to apply
        """
        self.hp = min(self.hp + amount, self.stats.get('max_hp', self.hp + amount))

    def cast_spell(self, spell_name, target):
        """
        Cast a spell.

        :param str spell_name: Name of the spell to cast
        :param Any target: Target of the spell
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
        Save the character to the database.

        Uses the ``characters`` table schema from db_init.py:
        name, class, level, hp, stats, inventory, spells.

        :param db_conn: Database connection object
        :type db_conn: sqlite3.Connection
        """
        cursor = db_conn.cursor()
        stats_json = json.dumps(self.stats)
        inv_json = json.dumps(self.inventory)
        spells_json = json.dumps(self.spells)

        cursor.execute(
            'INSERT INTO characters (name, "class", level, hp, stats, inventory, spells)'
            ' VALUES (?, ?, ?, ?, ?, ?, ?)',
            (
                self.name,
                self.char_class,
                self.level,
                self.hp,
                stats_json,
                inv_json,
                spells_json
            )
        )
        db_conn.commit()

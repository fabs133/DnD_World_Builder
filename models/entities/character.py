from models.entities.game_entity import GameEntity
from models.spell import Spell
import json


class Character(GameEntity):
    """
    Class representing a character.
    """

    def __init__(
        self,
        name,
        appearance,
        backstory,
        personality,
        languages,
        spellslots,
        spellcasting_ability,
        char_class,
        char_class_features,
        species,
        species_traits,
        subclass,
        feats,
        background,
        level,
        xp,
        armor_class,
        death_saves,
        hp,
        stats,
        inventory,
        training_proficiencies,
        spells,
        proficiency_bonus,
        hit_dice,
        saving_throws,
        skills,
        temporary_hp,
        inspiration,
        passive_perception,
        conditions,
        currency,
        exhaustion_level,
        armor,
        weapons,
        speed,
        initiative,
        resistances,
        immunities,
        vulnerabilities,
    ):
        """
        Initialize a character.

        :param str name: Name of the character
        :param str appearance: Appearance of the character
        :param str backstory: Backstory of the character
        :param str personality: Personality of the character
        :param list languages: List of languages known by the character
        :param dict spellslots: Dictionary of spell slots
        :param dict spellcasting_ability: Dictionary of spellcasting ability
        :param str char_class: Class of the character
        :param dict char_class_features: Dictionary of class features
        :param str species: Species of the character
        :param dict species_traits: Dictionary of species traits
        :param str subclass: Subclass of the character
        :param list feats: List of feats
        :param str background: Background of the character
        :param int level: Level of the character
        :param int xp: Experience points of the character
        :param int armor_class: Armor class of the character
        :param dict death_saves: Dictionary of death saves
        :param int hp: Hit points of the character
        :param dict stats: Dictionary of stats
        :param list inventory: List of items in the inventory
        :param dict training_proficiencies: Dictionary of training proficiencies
        :param list spells: List of spells
        :param int proficiency_bonus: Proficiency bonus of the character
        :param dict hit_dice: Dictionary of hit dice
        :param dict saving_throws: Dictionary of saving throws
        :param dict skills: Dictionary of skills
        :param int temporary_hp: Temporary hit points of the character
        :param bool inspiration: Boolean indicating if the character has inspiration
        :param int passive_perception: Passive perception of the character
        :param list conditions: List of conditions affecting the character
        :param dict currency: Dictionary of currency
        :param int exhaustion_level: Exhaustion level of the character
        :param list armor: List of armor
        :param list weapons: List of weapons
        :param int speed: Speed of the character
        :param int initiative: Initiative of the character
        :param list resistances: List of resistances
        :param list immunities: List of immunities
        :param list vulnerabilities: List of vulnerabilities
        """
        super().__init__(name, "player")
        self.name = name
        self.appearance = appearance
        self.backstory = backstory
        self.personality = personality
        self.languages = languages
        self.spellslots = spellslots
        self.spellcasting_ability = spellcasting_ability
        self.char_class = char_class
        self.char_class_features = char_class_features
        self.species = species
        self.species_traits = species_traits
        self.subclass = subclass
        self.feats = feats
        self.background = background
        self.level = level
        self.xp = xp
        self.proficiency_bonus = proficiency_bonus
        self.hit_dice = hit_dice
        self.armor_class = armor_class
        self.saving_throws = saving_throws
        self.skills = skills
        self.death_saves = death_saves
        self.hp = hp
        self.temporary_hp = temporary_hp
        self.stats = stats
        self.inventory = inventory
        self.training_proficiencies = training_proficiencies
        self.spells = spells
        self.inspiration = inspiration
        self.passive_perception = passive_perception
        self.conditions = conditions
        self.currency = currency
        self.spell_details = {spell['name']: spell for spell in spells}  # Store detailed spell information

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
        self.hp = min(self.hp + amount, self.stats['max_hp'])

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
            # The spell object will be automatically cleaned up by Python's garbage collector
            del spell  # Destroy the spell object after casting

    def save_to_db(self, db_conn):
        """
        Save the character to the database.

        Uses the ``characters`` table schema from db_init.py:
        name, class, level, hp, stats, inventory, spells.

        :param db_conn: Database connection object
        :type db_conn: sqlite3.Connection
        """
        cursor = db_conn.cursor()
        # Serialize JSON fields
        stats_json = json.dumps(self.stats)
        inv_json   = json.dumps(self.inventory)
        spells_json= json.dumps(self.spells)

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

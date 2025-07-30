from models.entities.enemy import Enemy
from models.spell import Spell
import json

class NamedEnemy(Enemy):
    """
    Represents a named enemy with additional lore, actions, and spellcasting abilities.

    Inherits from :class:`Enemy` and adds properties such as backstory, legendary actions,
    lair actions, regional effects, spellcasting ability, and combat phases.
    """

    def __init__(
        self, name, armor_class, hp, stats, saving_throws, attacks, speed,
        resistances, immunities, vulnerabilities, condition_immunities,
        challenge_rating, xp, conditions, initiative, spells,
        backstory, legendary_actions, lair_actions, regional_effects,
        spellcasting_ability, phases
    ):
        """
        Initialize a NamedEnemy instance.

        :param name: Name of the enemy.
        :type name: str
        :param armor_class: Armor class value.
        :type armor_class: int
        :param hp: Hit points.
        :type hp: int
        :param stats: Dictionary of stats (e.g., STR, DEX, etc.).
        :type stats: dict
        :param saving_throws: Saving throw modifiers.
        :type saving_throws: dict
        :param attacks: List of attacks.
        :type attacks: list
        :param speed: Movement speed.
        :type speed: int or dict
        :param resistances: List of resistances.
        :type resistances: list
        :param immunities: List of immunities.
        :type immunities: list
        :param vulnerabilities: List of vulnerabilities.
        :type vulnerabilities: list
        :param condition_immunities: List of condition immunities.
        :type condition_immunities: list
        :param challenge_rating: Challenge rating.
        :type challenge_rating: float or str
        :param xp: Experience points.
        :type xp: int
        :param conditions: List of conditions.
        :type conditions: list
        :param initiative: Initiative value.
        :type initiative: int
        :param spells: List of spells.
        :type spells: list
        :param backstory: Rich lore or story behind the enemy.
        :type backstory: str
        :param legendary_actions: List of legendary actions.
        :type legendary_actions: list
        :param lair_actions: List of lair actions.
        :type lair_actions: list
        :param regional_effects: List of regional effects.
        :type regional_effects: list
        :param spellcasting_ability: Spellcasting ability details.
        :type spellcasting_ability: dict
        :param phases: List of dictionaries representing combat phases.
        :type phases: list
        """
        # pass spells through to Enemy so self.spells & self.spell_details exist
        super().__init__(
            name, armor_class, hp, stats, saving_throws, attacks, speed,
            resistances, immunities, vulnerabilities, condition_immunities,
            challenge_rating, xp, conditions, initiative, spells
        )
        
        self.backstory = backstory
        self.legendary_actions = legendary_actions
        self.lair_actions = lair_actions
        self.regional_effects = regional_effects
        self.spellcasting_ability = spellcasting_ability
        self.phases = phases

    def take_damage(self, damage):
        """
        Apply damage to the enemy, reducing its hit points.

        :param damage: Amount of damage to apply.
        :type damage: int
        """
        self.hp = max(0, self.hp - damage)

    def heal(self, amount):
        """
        Heal the enemy, increasing its hit points up to max_hp.

        :param amount: Amount of hit points to restore.
        :type amount: int
        """
        self.hp = min(self.hp + amount, self.stats['max_hp'])

    def cast_spell(self, spell_name, target):
        """
        Cast a spell by name on a target.

        :param spell_name: Name of the spell to cast.
        :type spell_name: str
        :param target: Target of the spell.
        :type target: object
        """
        spell_data = next((spell for spell in self.spells if spell['name'] == spell_name), None)
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
            del spell  # Destroy the spell object after casting

    def save_to_db(self, db_conn):
        """
        Save the enemy's data to the database.

        :param db_conn: Database connection object.
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
            json.dumps(self.attacks)   # store attacks as "abilities"
        ))
        db_conn.commit()
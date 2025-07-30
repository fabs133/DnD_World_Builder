from models.flow.action.action import roll, apply_effect

class Spell:
    """
    Class representing a spell.

    :param name: Name of the spell
    :type name: str
    :param level: Spell level
    :type level: int
    :param school: School of magic (e.g., "Evocation", "Illusion")
    :type school: str
    :param casting_time: Casting time (e.g., "1 action", "1 minute")
    :type casting_time: str
    :param range: Range of the spell (e.g., "60 feet", "Self")
    :type range: str or None
    :param components: Components required (e.g., ["V", "S", "M"])
    :type components: list or None
    :param duration: Duration of the spell (e.g., "Instantaneous", "1 hour")
    :type duration: str or None
    :param description: Description of the spell's effects
    :type description: str
    :param damage: Optional. Dictionary: { "type": "fire", "amount": "2d6" }
    :type damage: dict or None
    :param healing: Optional. Dictionary: { "amount": "2d8" }
    :type healing: dict or None
    :param effect: Optional. Dictionary: { "type": "buff", "details": "Grants advantage on attack rolls" }
    :type effect: dict or None
    :param interrupt_difficulty: Difficulty to interrupt the spell (0-10 scale)
    :type interrupt_difficulty: int
    :param cast_priority: Priority of the spell in the casting order (e.g., "high", "medium", "low")
    :type cast_priority: str
    :param reaction_mode: String: "interrupt", "parallel" or "after"
    :type reaction_mode: str
    """

    def __init__(
        self,
        name,
        level,
        school,
        casting_time,
        range=None,
        components=None,
        duration=None,
        description="",
        damage=None,
        healing=None,
        effect=None,
        interrupt_difficulty=0,
        cast_priority="normal",
        reaction_mode="after"
    ):
        """
        Initialize a spell.

        See class docstring for parameter details.
        """
        self.name = name
        self.interrupt_difficulty = interrupt_difficulty
        self.cast_priority = cast_priority
        self.level = level
        self.school = school
        self.casting_time = casting_time
        self.range = range
        self.components = components
        self.duration = duration
        self.description = description
        self.damage = damage
        self.healing = healing
        self.effect = effect
        self.reaction_mode = reaction_mode

    def cast(self, caster, target):
        """
        Cast the spell from the caster to the target.

        :param caster: The entity casting the spell
        :type caster: object
        :param target: The target of the spell
        :type target: object
        """
        if self.damage:
            target.take_damage(self.calculate_damage())
        if self.healing:
            target.heal(self.calculate_healing())
        if self.effect:
            self.apply_effect(target)

    def calculate_damage(self):
        """
        Calculate the damage of the spell.

        :return: The amount of damage dealt
        :rtype: int
        """
        if self.damage and "amount" in self.damage:
            return roll(self.damage["amount"])
        return 0

    def calculate_healing(self):
        """
        Calculate the healing of the spell.

        :return: The amount of healing done
        :rtype: int
        """
        if self.healing and "amount" in self.healing:
            return roll(self.healing["amount"])
        return 0

    def apply_effect(self, target):
        """
        Apply the effect of the spell to the target.

        :param target: The target of the spell
        :type target: object
        """
        if self.effect:
            apply_effect(target, self.effect)
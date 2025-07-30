import random

class SkillCheck:
    """
    Represents a skill check in a DnD-like system.

    :param skill_name: The name of the skill (e.g., "perception", "athletics").
    :type skill_name: str
    :param dc: The difficulty class to beat.
    :type dc: int
    :param auto_pass: If True, the check automatically succeeds.
    :type auto_pass: bool, optional
    :param auto_fail: If True, the check automatically fails.
    :type auto_fail: bool, optional
    """
    def __init__(self, skill_name, dc, auto_pass=False, auto_fail=False):
        """
        Initialize a SkillCheck instance.

        :param skill_name: The name of the skill.
        :type skill_name: str
        :param dc: The difficulty class.
        :type dc: int
        :param auto_pass: Whether the check automatically passes.
        :type auto_pass: bool, optional
        :param auto_fail: Whether the check automatically fails.
        :type auto_fail: bool, optional
        """
        self.skill_name = skill_name  # e.g., "perception", "athletics"
        self.dc = dc
        self.auto_pass = auto_pass
        self.auto_fail = auto_fail

    def attempt(self, character_stats, advantage=False, disadvantage=False):
        """
        Attempt the skill check.

        :param character_stats: Dictionary mapping skill names to modifiers.
        :type character_stats: dict
        :param advantage: If True, roll with advantage.
        :type advantage: bool, optional
        :param disadvantage: If True, roll with disadvantage.
        :type disadvantage: bool, optional
        :return: True if the check succeeds, False otherwise.
        :rtype: bool
        """
        if self.auto_pass:
            return True
        if self.auto_fail:
            return False

        def roll():
            """
            Roll a d20.

            :return: Random integer between 1 and 20.
            :rtype: int
            """
            return random.randint(1, 20)

        if advantage:
            result = max(roll(), roll())
        elif disadvantage:
            result = min(roll(), roll())
        else:
            result = roll()

        modifier = character_stats.get(self.skill_name, 0)
        total = result + modifier
        return total >= self.dc

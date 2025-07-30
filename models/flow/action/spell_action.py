from .action import Action, roll, apply_effect

class SpellAction(Action):
    """
    Represents a spell action performed by a caster on one or more targets.

    :param caster: The entity casting the spell.
    :param spell: The spell object containing spell details.
    :param targets: A list of target entities affected by the spell.
    """
    def __init__(self, caster, spell, targets):
        """
        Initialize a SpellAction.

        :param caster: The entity casting the spell.
        :type caster: object
        :param spell: The spell being cast.
        :type spell: object
        :param targets: The targets of the spell.
        :type targets: list
        """
        super().__init__(caster)
        self.spell = spell
        self.targets = targets

    def validate(self, game_state):
        """
        Validate whether the spell can be cast in the current game state.

        Checks range, line of sight, components, etc.

        :param game_state: The current state of the game.
        :type game_state: object
        :return: None
        """
        pass

    def execute(self, game_state):
        """
        Execute the spell action, applying its effects to the targets.

        :param game_state: The current state of the game.
        :type game_state: object
        :return: None
        """
        for target in self.targets:
            if self.spell.damage:
                damage_roll = roll(self.spell.damage["amount"])
                target.take_damage(damage_roll, self.spell.damage["type"])
            if self.spell.healing:
                target.heal(roll(self.spell.healing["amount"]))
            if self.spell.effect:
                apply_effect(target, self.spell.effect)
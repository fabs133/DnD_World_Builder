from models.entities.game_entity import GameEntity

class Trap(GameEntity):
    """
    Represents a trap entity in the game.

    Inherits from :class:`GameEntity`.
    """

    def __init__(self, name, damage, trigger_range):
        """
        Initialize a Trap instance.

        :param name: The name of the trap.
        :type name: str
        :param damage: Damage dealt when the trap is triggered.
        :type damage: int
        :param trigger_range: The distance at which the trap is triggered.
        :type trigger_range: int
        """
        super().__init__(name, "trap")
        self.damage = damage
        self.trigger_range = trigger_range

    def take_turn(self):
        """
        Traps don't take actions, but they may be triggered during movement.
        """
        pass
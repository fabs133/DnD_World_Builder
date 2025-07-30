from models.entities.game_entity import GameEntity

class NPC(GameEntity):
    """
    Represents a Non-Player Character (NPC) in the game.

    Inherits from :class:`GameEntity`.
    """

    def __init__(self, name, behavior):
        """
        Initialize an NPC instance.

        :param name: The name of the NPC.
        :type name: str
        :param behavior: The behavior type of the NPC ("friendly", "hostile", or "neutral").
        :type behavior: str
        """
        super().__init__(name, "npc")
        self.behavior = behavior  # String : Could be "friendly", "hostile", or "neutral"

    def take_turn(self):
        """
        Defines the NPC's behavior during their turn.

        The action taken depends on the NPC's behavior attribute:
        - "friendly": May move around or interact with the player.
        - "neutral": May idle or react passively.
        - "hostile": May flee or attack.
        """
        if self.behavior == "friendly":
            # Maybe move around or interact with the player
            pass
        elif self.behavior == "neutral":
            # NPCs might idle or react passively
            pass
        elif self.behavior == "hostile":
            # Hostile NPCs could flee or attack
            pass
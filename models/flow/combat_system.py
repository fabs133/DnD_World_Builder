from core.logger import app_logger

class CombatSystem:
    """
    Handles the flow of combat between a player and an enemy.

    :param player: The player object participating in combat.
    :type player: Player
    :param enemy: The enemy object participating in combat.
    :type enemy: Enemy
    """

    def __init__(self, player, enemy):
        """
        Initialize the CombatSystem.

        :param player: The player object.
        :type player: Player
        :param enemy: The enemy object.
        :type enemy: Enemy
        """
        self.player = player  # Player object
        self.enemy = enemy    # Enemy object
        self.combat_round = 1 # Integer: Current round of combat

    def start_combat(self):
        """
        Initiate combat between the player and the enemy.

        This method announces the start of combat and begins the fight loop.
        """
        app_logger.info(f"Combat begins between {self.player.name} and {self.enemy.name}!")
        self.fight()

    def fight(self):
        """
        Handle combat actions, turn-by-turn.

        This method alternates turns between the player and the enemy until one is defeated.
        """
        while self.player.character.hp > 0 and self.enemy.hp > 0:
            app_logger.info(f"Round {self.combat_round}")
            # Player attacks
            self.player.take_turn()
            if self.enemy.hp <= 0:
                app_logger.info(f"{self.enemy.name} is defeated!")
                break

            # Enemy attacks
            self.enemy.take_turn()
            if self.player.character.hp <= 0:
                app_logger.info(f"{self.player.character.name} is defeated!")
                break

            self.combat_round += 1
        app_logger.info("Combat ends.")
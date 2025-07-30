from abc import ABC, abstractmethod
import random
import re

class Action(ABC):
    """
    Abstract base class for actions performed by game entities.

    Defines the structure for validating and executing actions.
    """

    def __init__(self, actor):
        """
        Initialize an action with the actor performing it.

        :param actor: The GameEntity performing the action.
        """
        self.actor = actor
        self.validated = False  #: Whether the action has been validated.
        self.blocked = False    #: Whether the action has been blocked.
        self.execution_log = [] #: Log of events during the action's execution.

    @abstractmethod
    def validate(self, game_state):
        """
        Validate whether the action can be performed under the current game state.

        Must be implemented by subclasses.

        :param game_state: The current state of the game.
        :type game_state: object
        :raises NotImplementedError: If not implemented in subclass.
        """
        pass

    @abstractmethod
    def execute(self, game_state):
        """
        Execute the action's effects on the game state.

        Must be implemented by subclasses.

        :param game_state: The current state of the game.
        :type game_state: object
        :raises NotImplementedError: If not implemented in subclass.
        """
        pass

    def interrupt(self, reason):
        """
        Interrupt the action, marking it as blocked and logging the reason.

        :param reason: The reason for the interruption.
        :type reason: str
        """
        self.blocked = True
        self.execution_log.append(f"Action interrupted: {reason}")

    @staticmethod
    def roll(expression):
        """
        Parse and roll a dice expression (e.g., '2d6+3') and return the result.

        :param expression: A string representing the dice roll (e.g., '2d6+3').
        :type expression: str
        :return: The total result of the dice roll.
        :rtype: int
        :raises ValueError: If the dice expression is invalid.
        """
        match = re.match(r"(\d*)d(\d+)([+-]?\d*)", expression.replace(" ", ""))
        if not match:
            raise ValueError(f"Invalid dice expression: {expression}")

        num_dice = int(match.group(1)) if match.group(1) else 1
        dice_sides = int(match.group(2))
        modifier = int(match.group(3)) if match.group(3) else 0

        rolls = [random.randint(1, dice_sides) for _ in range(num_dice)]
        total = sum(rolls) + modifier
        print(f"Rolling {expression}: {rolls} + {modifier} = {total}")
        return total

    @staticmethod
    def apply_effect(target, effect):
        """
        Apply an effect to a target.

        :param target: GameEntity receiving the effect.
        :type target: object
        :param effect: Dictionary describing the effect.
        :type effect: dict
        :example effect: {
            "type": "buff",
            "details": "advantage on attack rolls",
            "duration": 3
        }
        """
        effect_type = effect.get("type")
        details = effect.get("details", "")
        duration = effect.get("duration", 1)  # Default 1 round

        # For now, we’ll store simple status effects as a list of dicts on the target
        if not hasattr(target, "active_effects"):
            target.active_effects = []

        target.active_effects.append({
            "type": effect_type,
            "details": details,
            "duration": duration
        })

        print(f"{target.name} gains effect: {effect_type} ({details}) for {duration} rounds.")

roll = Action.roll
apply_effect = Action.apply_effect
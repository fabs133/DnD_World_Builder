from models.flow.reaction.reactions import Reactions
from core.logger import app_logger

class ApplyDamage(Reactions):
    """
    Reaction that applies damage to a target.

    :param damage_type: The type of damage to apply (e.g., "fire", "bludgeoning").
    :type damage_type: str
    :param amount: The amount of damage to apply.
    :type amount: int
    """
    def __init__(self, damage_type: str, amount: int):
        """
        Initialize an ApplyDamage reaction.

        :param damage_type: The type of damage.
        :type damage_type: str
        :param amount: The amount of damage.
        :type amount: int
        """
        self.damage_type = damage_type
        self.amount = amount

    def __call__(self, event_data):
        """
        Apply damage to the target in the event data.

        :param event_data: Dictionary containing event information, must include 'target'.
        :type event_data: dict
        """
        target = event_data.get("target")
        if hasattr(target, "take_damage"):
            target.take_damage(self.amount, self.damage_type)
        else:
            app_logger.warning(f"[ApplyDamage] Invalid or missing target in event_data: {event_data}")

    def to_dict(self):
        """
        Serialize the reaction to a dictionary.

        :return: Dictionary representation of the reaction.
        :rtype: dict
        """
        return {
            "type": "ApplyDamage",
            "damage_type": self.damage_type,
            "amount": self.amount
        }

    @classmethod
    def from_dict(cls, data):
        """
        Create an ApplyDamage reaction from a dictionary.

        :param data: Dictionary containing 'damage_type' and 'amount'.
        :type data: dict
        :return: An instance of ApplyDamage.
        :rtype: ApplyDamage
        """
        return cls(data["damage_type"], data["amount"])

class AlertGamemaster(Reactions):
    """
    Reaction that alerts the gamemaster with a message.

    :param message: The message to send to the gamemaster.
    :type message: str
    """
    def __init__(self, message: str):
        """
        Initialize an AlertGamemaster reaction.

        :param message: The message to alert the gamemaster.
        :type message: str
        """
        self.message = message

    def __call__(self, event_data):
        """
        Alert the gamemaster with the specified message.

        :param event_data: Dictionary containing event information, may include 'game'.
        :type event_data: dict
        """
        app_logger.info(f"[GM ALERT] {self.message}")
        if "game" in event_data and hasattr(event_data["game"], "flag_event"):
            event_data["game"].flag_event(self.message)

    def to_dict(self):
        """
        Serialize the reaction to a dictionary.

        :return: Dictionary representation of the reaction.
        :rtype: dict
        """
        return {
            "type": "AlertGamemaster",
            "message": self.message
        }

    @classmethod
    def from_dict(cls, data):
        """
        Create an AlertGamemaster reaction from a dictionary.

        :param data: Dictionary containing 'message'.
        :type data: dict
        :return: An instance of AlertGamemaster.
        :rtype: AlertGamemaster
        """
        return cls(message=data["message"])

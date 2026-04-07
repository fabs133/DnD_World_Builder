from models.flow.reaction.reactions import Reactions
from core.logger import app_logger

class ApplyDamage(Reactions):
    """
    Reaction that applies damage to a target.

    :param damage_type: The type of damage to apply (e.g., "fire", "bludgeoning").
    :type damage_type: str
    :param amount: Fixed amount of damage. Ignored when *damage_expr* is set.
    :type amount: int
    :param damage_expr: Optional dice expression (e.g. "2d6") rolled each time
        the reaction fires.  Takes priority over *amount*.
    :type damage_expr: str or None
    """
    def __init__(self, damage_type: str, amount: int = 0, damage_expr: str | None = None):
        self.damage_type = damage_type
        self.amount = amount
        self.damage_expr = damage_expr

    def _resolve_amount(self) -> int:
        """Return damage amount, rolling dice expression if present."""
        if self.damage_expr:
            from models.flow.action.action import Action
            return Action.roll(self.damage_expr)
        return self.amount

    def __call__(self, event_data):
        """
        Apply damage to the target in the event data.

        :param event_data: Dictionary containing event information, must include 'target'.
        :type event_data: dict
        """
        target = event_data.get("target")
        if hasattr(target, "take_damage"):
            target.take_damage(self._resolve_amount(), self.damage_type)
        else:
            app_logger.warning(f"[ApplyDamage] Invalid or missing target in event_data: {event_data}")

    def to_dict(self):
        """
        Serialize the reaction to a dictionary.

        :return: Dictionary representation of the reaction.
        :rtype: dict
        """
        d = {
            "type": "ApplyDamage",
            "damage_type": self.damage_type,
            "amount": self.amount,
        }
        if self.damage_expr:
            d["damage_expr"] = self.damage_expr
        return d

    @classmethod
    def from_dict(cls, data):
        """
        Create an ApplyDamage reaction from a dictionary.

        :param data: Dictionary containing 'damage_type' and 'amount'.
        :type data: dict
        :return: An instance of ApplyDamage.
        :rtype: ApplyDamage
        """
        return cls(
            data["damage_type"],
            data.get("amount", 0),
            damage_expr=data.get("damage_expr"),
        )

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
        # Broadcast to narration UI
        try:
            from core.gameCreation.event_bus import EventBus
            from core.events import NARRATION_TRIGGERED
            EventBus.emit(NARRATION_TRIGGERED, {
                "message": self.message,
                "source": "trigger",
            })
        except Exception:
            pass

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

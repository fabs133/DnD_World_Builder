from models.flow.condition.condition import Condition

class AlwaysTrue(Condition):
    """
    Condition that always evaluates to True.
    """

    def __call__(self, event_data):
        """
        Always returns True, regardless of input.

        :param event_data: Arbitrary event data (unused).
        :type event_data: dict
        :return: Always True.
        :rtype: bool
        """
        return True

    def to_dict(self):
        """
        Serialize the condition to a dictionary.

        :return: Dictionary representation of the condition.
        :rtype: dict
        """
        return {"type": "AlwaysTrue"}

    @classmethod
    def from_dict(cls, data):
        """
        Create an AlwaysTrue condition from a dictionary.

        :param data: Dictionary containing condition data.
        :type data: dict
        :return: An instance of AlwaysTrue.
        :rtype: AlwaysTrue
        """
        return cls()

class PerceptionCheck(Condition):
    """
    Condition that checks if the perception value meets or exceeds a difficulty class (DC).
    """

    def __init__(self, dc):
        """
        Initialize the PerceptionCheck condition.

        :param dc: The difficulty class to check against.
        :type dc: int
        """
        self.dc = dc

    def __call__(self, event_data):
        """
        Check if the perception value in event_data meets or exceeds the DC.

        :param event_data: Event data containing a 'perception' value.
        :type event_data: dict
        :return: True if perception >= dc, False otherwise.
        :rtype: bool
        """
        try:
            perception = int(event_data.get("perception", 0))
            return perception >= self.dc
        except (TypeError, ValueError):
            print(f"[⚠️ PerceptionCheck] Invalid perception value in: {event_data}")
            return False

    def to_dict(self):
        """
        Serialize the condition to a dictionary.

        :return: Dictionary representation of the condition.
        :rtype: dict
        """
        return {"type": "PerceptionCheck", "dc": self.dc}

    @classmethod
    def from_dict(cls, data):
        """
        Create a PerceptionCheck condition from a dictionary.

        :param data: Dictionary containing condition data.
        :type data: dict
        :return: An instance of PerceptionCheck.
        :rtype: PerceptionCheck
        """
        return cls(data["dc"])

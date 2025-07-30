class Condition:
    """
    Base class for defining conditions in the flow.

    Subclasses should implement the required methods.
    """

    def __call__(self, event_data: dict) -> bool:
        """
        Evaluate the condition with the provided event data.

        :param event_data: Dictionary containing event-specific data.
        :type event_data: dict
        :return: True if the condition is met, False otherwise.
        :rtype: bool
        :raises NotImplementedError: If not implemented in subclass.
        """
        raise NotImplementedError

    def to_dict(self):
        """
        Serialize the condition to a dictionary.

        :return: Dictionary representation of the condition.
        :rtype: dict
        :raises NotImplementedError: If not implemented in subclass.
        """
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data):
        """
        Create a condition instance from a dictionary.

        :param data: Dictionary containing the condition data.
        :type data: dict
        :return: An instance of the condition.
        :rtype: Condition
        :raises NotImplementedError: If not implemented in subclass.
        """
        raise NotImplementedError

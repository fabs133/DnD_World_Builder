class Reactions:
    """
    Base class for reaction handlers.

    This class should be subclassed to implement specific reaction logic.
    """

    def __call__(self, event_data: dict):
        """
        Execute the reaction with the provided event data.

        :param event_data: Dictionary containing event-specific data.
        :type event_data: dict
        :raises NotImplementedError: If not implemented in a subclass.
        """
        raise NotImplementedError

    def to_dict(self):
        """
        Serialize the reaction to a dictionary.

        :returns: A dictionary representation of the reaction.
        :rtype: dict
        :raises NotImplementedError: If not implemented in a subclass.
        """
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data):
        """
        Create a reaction instance from a dictionary.

        :param data: Dictionary containing the reaction data.
        :type data: dict
        :returns: An instance of the reaction.
        :rtype: Reactions
        :raises NotImplementedError: If not implemented in a subclass.
        """
        raise NotImplementedError

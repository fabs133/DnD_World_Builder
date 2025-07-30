class Reaction:
    """
    Represents a reaction to a trigger action in the flow.

    Attributes
    ----------
    reactor : object
        The entity performing the reaction.
    trigger_action : object
        The action that triggered this reaction.
    """

    def __init__(self, reactor, trigger_action):
        """
        Initialize a Reaction instance.

        Parameters
        ----------
        reactor : object
            The entity performing the reaction.
        trigger_action : object
            The action that triggered this reaction.
        """
        self.reactor = reactor  # Who is reacting
        self.trigger_action = trigger_action  # The action they are reacting to

    def resolve(self):
        """
        Resolve the reaction.

        This method implements the logic of the reaction. It could interrupt,
        modify, or negate the original action.

        Returns
        -------
        None
        """
        print(f"{self.reactor.name} reacts to {self.trigger_action}!")
        # Example: negate the action or inflict damage
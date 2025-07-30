class ReactionQueue:
    """
    A queue to manage and resolve reaction objects.

    Reactions are expected to have a `resolve()` method.
    """

    _queue = []

    @classmethod
    def add(cls, reaction):
        """
        Add a reaction to the queue.

        Parameters
        ----------
        reaction : object
            An object with at least a `resolve()` method.
        """
        cls._queue.append(reaction)
        print(f"[ReactionQueue] Added reaction: {reaction}")

    @classmethod
    def blocked(cls):
        """
        Check if execution is currently blocked by pending reactions.

        Returns
        -------
        bool
            True if there are pending reactions in the queue, False otherwise.
        """
        return len(cls._queue) > 0

    @classmethod
    def resolve(cls):
        """
        Resolve all queued reactions in order.

        Each reaction's `resolve()` method is called. If an exception occurs,
        it is caught and printed, and resolution continues with the next reaction.
        """
        print("[ReactionQueue] Resolving reactions...")
        while cls._queue:
            reaction = cls._queue.pop(0)
            try:
                reaction.resolve()
            except Exception as e:
                print(f"[ReactionQueue] Error resolving {reaction}: {e}")
        print("[ReactionQueue] All reactions resolved.")

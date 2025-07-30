class TurnManager:
    """
    Manages turn-based scheduling and execution of callbacks.

    Attributes
    ----------
    current_turn : int
        The current turn number.
    _scheduled : list
        List of scheduled callbacks as tuples (target_turn, callback, data).
    """

    def __init__(self):
        """
        Initialize the TurnManager with turn counter and scheduled callbacks.
        """
        self.current_turn = 0
        self._scheduled = []  # list of (target_turn, callback, data)

    def schedule_in(self, turns: int, callback, data):
        """
        Schedule a callback to be executed after a given number of turns.

        Parameters
        ----------
        turns : int
            Number of turns to wait before executing the callback.
        callback : callable
            The function to call when the scheduled turn is reached.
        data : any
            Data to pass to the callback function.
        """
        target = self.current_turn + turns
        self._scheduled.append((target, callback, data))

    def _dispatch_scheduled(self):
        """
        Dispatch and execute all callbacks scheduled for the current turn.
        """
        # fire any callbacks scheduled for this turn
        to_run = [s for s in self._scheduled if s[0] == self.current_turn]
        for target, cb, data in to_run:
            cb(data)
            self._scheduled.remove((target, cb, data))

    def next_turn(self):
        """
        Advance to the next turn and dispatch any scheduled callbacks.
        """
        self.current_turn += 1
        self._dispatch_scheduled()

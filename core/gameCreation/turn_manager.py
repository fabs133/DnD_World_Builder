class TurnManager:
    """
    Manages turn-based scheduling and execution of callbacks.

    This class allows scheduling callbacks to be executed after a certain number of turns.
    """

    def __init__(self):
        """
        Initializes the TurnManager.

        Attributes:
            current_turn (int): The current turn number.
            _queue (list): Internal queue of scheduled callbacks.
        """
        self.current_turn = 0
        self._queue = []

    def schedule_in(self, turns: int, callback, data=None):
        """
        Schedule a callback to be executed after a given number of turns.

        :param turns: Number of turns to wait before executing the callback.
        :type turns: int
        :param callback: The function to call when the scheduled turn is reached.
        :type callback: callable
        :param data: Optional data to pass to the callback.
        :type data: any, optional
        """
        fire_turn = self.current_turn + turns
        self._queue.append((fire_turn, callback, data))

    def _dispatch_due(self):
        """
        Dispatches all callbacks scheduled for the current turn.

        This method is called internally to execute all callbacks whose scheduled turn matches the current turn.
        """
        due = [(cb, d) for (t, cb, d) in self._queue if t == self.current_turn]
        self._queue = [(t, cb, d) for (t, cb, d) in self._queue if t != self.current_turn]
        for cb, data in due:
            cb(data)

    def next_turn(self):
        """
        Advances to the next turn and dispatches any due callbacks.

        :return: The new current turn number.
        :rtype: int
        """
        self.current_turn += 1
        self._dispatch_due()
        # then whatever else you need: e.g. logging, round increments, etc.
        return self.current_turn

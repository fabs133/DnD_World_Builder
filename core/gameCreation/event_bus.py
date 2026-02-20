from core.logger import app_logger


class EventBus:
    """
    Singleton event bus for subscribing to and emitting events within the game.

    Uses a proper singleton pattern where subscriber state lives on the
    single instance rather than at the class level. The public API remains
    classmethod-based for convenience.
    """
    _instance = None

    def __init__(self):
        self._subscribers = {}

    @classmethod
    def _get_instance(cls):
        """Return (and lazily create) the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def subscribe(cls, event_type, callback):
        """
        Subscribe a callback to a specific event type.

        :param event_type: The type of event to subscribe to.
        :type event_type: str
        :param callback: The function to call when the event is emitted.
        :type callback: callable
        """
        inst = cls._get_instance()
        if event_type not in inst._subscribers:
            inst._subscribers[event_type] = []
        if callback not in inst._subscribers[event_type]:
            inst._subscribers[event_type].append(callback)

    @classmethod
    def unsubscribe(cls, event_type, callback):
        """
        Unsubscribe a callback from a specific event type.

        :param event_type: The type of event to unsubscribe from.
        :type event_type: str
        :param callback: The function to remove from the subscriber list.
        :type callback: callable
        """
        inst = cls._get_instance()
        if event_type in inst._subscribers:
            try:
                inst._subscribers[event_type].remove(callback)
            except ValueError:
                pass

    @classmethod
    def emit(cls, event_type, data):
        """
        Emit an event to all relevant subscribers.

        If 'position' and 'world' are present in data, notifies entities at the position
        and those within line-of-sight. Otherwise, performs a global broadcast.

        :param event_type: The type of event to emit.
        :type event_type: str
        :param data: The event data, must be a dict. Should contain 'position' and 'world' for spatial events.
        :type data: dict
        """
        inst = cls._get_instance()
        pos   = data.get("position")
        world = data.get("world")

        if pos is not None and world is not None:
            # 1) the entity (trap) on that tile
            for ent in world.get_entities_at(*pos):
                ent.handle_event(event_type, data)

            # 2) proximity: anyone with no range, or anyone within line-of-sight, gets notified
            for (x, y), ents in world.tile_manager.entities.items():
                if (x, y) == pos:
                    continue
                for ent in ents:
                    vr = getattr(ent, "vision_range", None)
                    # if no vision_range is set, or if they can see the source tile, notify
                    if vr is None or world.can_see(pos, ent.position, vr):
                        ent.handle_event(event_type, data)
        else:
            # global broadcast
            for cb in inst._subscribers.get(event_type, []):
                cb(data)

    @classmethod
    def reset(cls):
        """
        Reset the event bus, clearing all subscribers.

        Emits a warning via the application logger.
        """
        inst = cls._get_instance()
        app_logger.warning("EventBus reset — all subscribers cleared.")
        inst._subscribers.clear()

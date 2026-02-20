from registries.condition_registry import ConditionRegistry
from registries.reaction_registry import ReactionRegistry
from core.logger import app_logger

class TriggerRegistry:
    """
    Registry for managing triggers, their associated functions, and their sources.

    Attributes
    ----------
    condition_registry : ConditionRegistry
        Registry for conditions.
    reaction_registry : ReactionRegistry
        Registry for reactions.
    """

    def __init__(self):
        """
        Initialize a new TriggerRegistry.
        """
        self._triggers = set()  # Unique Trigger objects
        self.condition_registry = ConditionRegistry()
        self.reaction_registry = ReactionRegistry()
        self._function_lookup = {}  # func_name → function
        self._source_map = {}  # Trigger → str (e.g., entity name or origin)

    def register_function(self, func, name=None):
        """
        Register a function for use by triggers.

        Parameters
        ----------
        func : callable
            The function to register.
        name : str, optional
            The name to register the function under. If None, uses func.__name__.
        """
        key = name or func.__name__
        self._function_lookup[key] = func

    def get_function(self, name):
        """
        Retrieve a registered function by name.

        Parameters
        ----------
        name : str
            The name of the function.

        Returns
        -------
        callable or None
            The registered function, or None if not found.
        """
        return self._function_lookup.get(name)

    def add_trigger(self, trigger, source=None):
        """
        Add a trigger to the registry.

        Parameters
        ----------
        trigger : object
            The trigger object to add.
        source : str, optional
            The source or origin of the trigger.

        Returns
        -------
        bool
            True if the trigger was added, False if it already exists.
        """
        if trigger in self._triggers:
            return False  # Already exists

        self._triggers.add(trigger)
        self._source_map[trigger] = source or "unknown"
        return True

    def is_registered(self, trigger):
        """
        Check if a trigger is registered.

        Parameters
        ----------
        trigger : object
            The trigger to check.

        Returns
        -------
        bool
            True if the trigger is registered, False otherwise.
        """
        return trigger in self._triggers

    def remove_trigger(self, trigger):
        """
        Remove a trigger from the registry.

        Parameters
        ----------
        trigger : object
            The trigger to remove.
        """
        self._triggers.discard(trigger)
        self._source_map.pop(trigger, None)

    def get_all_triggers(self):
        """
        Get a list of all registered triggers.

        Returns
        -------
        list
            List of all registered triggers.
        """
        return list(self._triggers)

    def get_source(self, trigger):
        """
        Get the source associated with a trigger.

        Parameters
        ----------
        trigger : object
            The trigger to query.

        Returns
        -------
        str
            The source of the trigger, or "unknown" if not found.
        """
        return self._source_map.get(trigger, "unknown")

    def debug_print(self):
        """
        Log debug information about all registered triggers.
        """
        app_logger.debug("TriggerRegistry:")
        for t in self._triggers:
            src = self.get_source(t)
            app_logger.debug(f"  {t.event_type} (from: {src})")
    
    def get_triggers_by_source(self, source_name):
        """
        Get all triggers registered from a specific source.

        Parameters
        ----------
        source_name : str
            The name of the source.

        Returns
        -------
        list
            List of triggers from the specified source.
        """
        return [t for t in self._triggers if self._source_map.get(t) == source_name]


# Create a global instance
global_trigger_registry = TriggerRegistry()

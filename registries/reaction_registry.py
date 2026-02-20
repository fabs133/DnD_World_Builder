from models.flow.reaction.reactions_list import ApplyDamage, AlertGamemaster
from models.flow.reaction.play_sound import PlaySound

class ReactionRegistry:
    """
    Registry for reaction classes.

    This class allows registering, retrieving, and instantiating reaction classes by name.
    """

    def __init__(self):
        """
        Initialize the ReactionRegistry with an empty registry.
        """
        self._registry = {}

    def register(self, name, cls):
        """
        Register a reaction class with a given name.

        :param name: The name to register the class under.
        :type name: str
        :param cls: The class to register.
        :type cls: type
        """
        self._registry[name] = cls

    def create(self, data: dict):
        """
        Create an instance of a registered reaction class from a dictionary.

        :param data: Dictionary containing at least a "type" key.
        :type data: dict
        :raises ValueError: If the type is not registered.
        :return: An instance of the registered class.
        """
        cls = self._registry.get(data["type"])
        if not cls:
            raise ValueError(f"[Condition] Unknown type: {data['type']}")
        return cls.from_dict(data)

    def get_all(self):
        """
        Get a list of all registered reaction names.

        :return: List of registered names.
        :rtype: list
        """
        return list(self._registry.keys())

    def get_class(self, name):
        """
        Get the class registered under the given name.

        :param name: The name of the registered class.
        :type name: str
        :return: The registered class or None if not found.
        """
        return self._registry.get(name)
    
    def list_keys(self):
        """
        Alias for get_all(). Returns all registered reaction names.

        :return: List of registered names.
        :rtype: list
        """
        return self.get_all()


reaction_registry = ReactionRegistry()
reaction_registry.register("ApplyDamage", ApplyDamage)
reaction_registry.register("AlertGamemaster", AlertGamemaster)
reaction_registry.register("PlaySound", PlaySound)

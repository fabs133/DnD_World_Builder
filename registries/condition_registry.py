from models.flow.condition.condition_list import AlwaysTrue, PerceptionCheck

class ConditionRegistry:
    """
    Registry for condition classes.

    This class allows registering, retrieving, and instantiating condition classes by name.
    """

    def __init__(self):
        """
        Initialize an empty condition registry.
        """
        self._registry = {}

    def register(self, name, cls):
        """
        Register a condition class with a given name.

        :param name: The name to register the class under.
        :type name: str
        :param cls: The class to register.
        :type cls: type
        """
        self._registry[name] = cls

    def create(self, data: dict):
        """
        Create an instance of a registered condition class from a dictionary.

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
        Get a list of all registered condition names.

        :return: List of registered condition names.
        :rtype: list[str]
        """
        return list(self._registry.keys())

    def list_keys(self):
        """
        Alias for :meth:`get_all`.

        :return: List of registered condition names.
        :rtype: list[str]
        """
        return self.get_all()

    def get_class(self, name):
        """
        Get the registered class for a given name.

        :param name: The name of the registered class.
        :type name: str
        :return: The registered class, or None if not found.
        :rtype: type or None
        """
        return self._registry.get(name)


condition_registry = ConditionRegistry()
condition_registry.register("AlwaysTrue", AlwaysTrue)
condition_registry.register("PerceptionCheck", PerceptionCheck)
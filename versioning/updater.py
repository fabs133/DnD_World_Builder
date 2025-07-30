class Updater:
    """
    Module for handling versioned data migrations using a registry of migration functions.

    This class applies sequential migrations to data entities based on their type and version.
    """

    def __init__(self, registry):
        """
        Initialize the Updater with a migration registry.

        :param registry: A dictionary mapping entity types to their migration functions.
                         Each value should be a dict mapping version numbers to migration callables.
        :type registry: dict
        """
        self.registry = registry

    def update(self, entity_type, data, current_version):
        """
        Update the given data entity to the latest version using registered migrations.

        :param entity_type: The type of the entity to update.
        :type entity_type: str
        :param data: The data to be migrated.
        :type data: dict
        :param current_version: The current version of the data.
        :type current_version: int
        :return: The migrated data at the latest version.
        :rtype: dict
        :raises ValueError: If there are no migrations registered for the given entity type.
        :raises TypeError: If a migration function does not return a dictionary.
        """
        if entity_type not in self.registry:
            raise ValueError(f"No migrations for {entity_type}")

        migrations = self.registry[entity_type]
        version = current_version
        while version in migrations:
            migrate_fn = migrations[version]
            if migrate_fn is None:
                break

            new_data = migrate_fn(data)
            if not isinstance(new_data, dict):
                raise TypeError(f"Migration for version {version} did not return a dict")

            # advance the version: use explicit or assume 1
            version = new_data.get("version", version + 1)
            data = new_data

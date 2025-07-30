from .rulebook_entity import RulebookEntity
from core.db_api_handler import LocalAPIHandler
from utils.string.slugify import slugify
from core.rulebook.importer_base import BaseImporter

class EntityImporter(BaseImporter):
    """
    Imports and parses monster entities from a local SRD JSON dataset.

    Inherits:
        BaseImporter: Provides API setup and slugified endpoint access.

    :param api: Optional API handler instance (LocalAPIHandler or similar)
    :type api: object
    """

    def __init__(self, api=None, base_path="core/data/rulebook_json"):
        if api is None:
            api = LocalAPIHandler(base_path)
        super().__init__(api=api)
        self.endpoint = "monsters"

    def parse(self, raw: dict) -> RulebookEntity:
        """
        Parse raw monster data into a RulebookEntity.

        :param raw: The raw monster dictionary.
        :type raw: dict
        :return: A RulebookEntity instance.
        :rtype: RulebookEntity
        """
        return RulebookEntity.from_monster(raw)

    def list_all(self):
        """
        Retrieve the full list of monster definitions.

        :return: A list of all monster entries.
        :rtype: list[dict]
        """
        return self.api.get(self.endpoint)

    def get_by_name(self, name: str) -> RulebookEntity | None:
        """
        Retrieve a monster by name and parse it into a RulebookEntity.

        :param name: The monster's name (e.g., "Goblin").
        :type name: str
        :return: A RulebookEntity instance if found, otherwise None.
        :rtype: RulebookEntity or None
        """
        slug = slugify(name)
        raw = self.api.get_raw(f"/api/{self.endpoint}/{slug}")
        return RulebookEntity.from_monster(raw) if raw else None

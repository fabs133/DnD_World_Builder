from .importer_base import BaseImporter
from .rulebook_spell import RulebookSpell
from core.db_api_handler import LocalAPIHandler
from utils.string.slugify import slugify
from core.rulebook.importer_base import BaseImporter

class SpellImporter(BaseImporter):
    """
    Imports and parses spells from a local SRD JSON dataset.

    Inherits:
        BaseImporter: Provides API setup and slugified endpoint access.

    :param api: Optional API handler instance (LocalAPIHandler or similar)
    :type api: object
    """

    def __init__(self, api=None, base_path="core/data_/rulebook_json"):
        super().__init__(api=api, base_path=base_path)
        self.endpoint = "spells"


    def parse(self, raw):
        """
        Parses raw spell data from the API into a RulebookSpell object.

        :param raw: The raw spell data from the API.
        :type raw: dict
        :return: A RulebookSpell instance created from the raw data.
        :rtype: RulebookSpell
        """
        return RulebookSpell.from_api(raw)
    
    def list_all(self):
        """
        Retrieves a list of all spells from the API.

        :return: A list of all spells from the API.
        :rtype: list
        """
        return self.api.get(self.endpoint)

    def get_by_name(self, name: str) -> RulebookSpell:
        """
        Retrieves a spell by its name.

        :param name: The name of the spell to retrieve.
        :type name: str
        :return: A RulebookSpell instance if found, otherwise None.
        :rtype: RulebookSpell or None
        """
        slug = slugify(name)
        raw = self.api.get_raw(f"/api/{self.endpoint}/{slug}")
        return RulebookSpell.from_api(raw) if raw else None
    
import re
from core.db_api_handler import LocalAPIHandler  # Make sure this import is correct

class BaseImporter:
    """
    BaseImporter provides basic functionality for importing data from a local SRD JSON dataset.

    Attributes
    ----------
    api : LocalAPIHandler
        An instance used to access SRD data from disk.
    """

    def __init__(self, api=None, base_path="core/data_/rulebook_json"):
        if api is not None:
            self.api = api
        else:
            from core.db_api_handler import LocalAPIHandler
            self.api = LocalAPIHandler(base_path)

    def slugify(self, name: str) -> str:
        """
        Converts a string into a slug suitable for SRD matching.
        """
        name = name.strip().lower()
        name = re.sub(r"[^\w\s-]", "", name)
        return re.sub(r"\s+", "-", name)

    def get_raw(self, category: str, name: str) -> dict:
        """
        Retrieves a single entry by category and name using a slug-based lookup.

        Parameters
        ----------
        category : str
            Category name (e.g. "monsters", "spells").
        name : str
            Display name (e.g. "Goblin").

        Returns
        -------
        dict
            The matching JSON entry, or None if not found.
        """
        slug = self.slugify(name)
        endpoint = f"/api/{category}/{slug}"
        return self.api.get_raw(endpoint)

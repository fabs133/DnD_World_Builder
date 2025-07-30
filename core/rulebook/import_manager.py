from .entity_importer import EntityImporter
from .spell_importer import SpellImporter
from models.entities.game_entity import GameEntity
from models.spell import Spell
from core.db_api_handler import LocalAPIHandler


class RulebookImporter:
    """
    Handles importing monsters and spells from local SRD JSON files.
    """

    def __init__(self, base_path="core/data_/rulebook_json"):
        """
        Initializes the RulebookImporter using local rulebook data.

        :param base_path: Path to the directory containing SRD JSON files.
        :type base_path: str
        """
        shared_api = LocalAPIHandler(base_path)
        self.monsters = EntityImporter(api=shared_api)
        self.spells = SpellImporter(api=shared_api)

    def search_monsters(self):
        """
        Retrieves a list of all monster names from the local SRD.

        :return: A list of monster names.
        :rtype: list[str]
        """
        results = self.monsters.list_all()
        if not results:
            return []
        return [entry["name"] for entry in results]

    def search_spells(self):
        """
        Retrieves a list of all spell names from the local SRD.

        :return: A list of spell names.
        :rtype: list[str]
        """
        results = self.spells.list_all()
        if not results:
            return []
        return [entry["name"] for entry in results]

    def import_monster(self, name: str) -> GameEntity:
        """
        Imports a monster by name and converts it to a GameEntity.

        :param name: The name of the monster to import.
        :type name: str
        :return: The imported monster as a GameEntity, or None on error.
        :rtype: GameEntity or None
        """
        try:
            rbe = self.monsters.get_by_name(name)
            return rbe.to_game_entity() if rbe else None
        except Exception as e:
            print(f"[Importer] Failed to import monster '{name}': {e}")
            return None

    def import_spell(self, name: str) -> Spell:
        """
        Imports a spell by name and converts it to a Spell object.

        :param name: The name of the spell to import.
        :type name: str
        :return: The imported spell as a Spell object, or None on error.
        :rtype: Spell or None
        """
        try:
            rbs = self.spells.get_by_name(name)
            return rbs.to_spell() if rbs else None
        except Exception as e:
            print(f"[Importer] Failed to import spell '{name}': {e}")
            return None

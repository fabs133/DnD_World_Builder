class RulebookEntity:
    """
    Represents a generic entity from a rulebook, such as a monster, NPC, spell, or item.

    :param name: The name of the entity.
    :type name: str
    :param entity_type: The type/category of the entity (e.g., "monster", "npc", "spell", "item").
    :type entity_type: str
    :param stats: A dictionary containing the entity's statistics (e.g., HP, AC, abilities).
    :type stats: dict, optional
    :param abilities: A list of the entity's abilities or actions.
    :type abilities: list, optional
    :param source: The source type of the entity (e.g., "monster", "spell").
    :type source: str, optional
    :param raw_data: The raw data dictionary from which the entity was created.
    :type raw_data: dict, optional

    :ivar name: The name of the entity.
    :ivar entity_type: The type/category of the entity.
    :ivar stats: The entity's statistics.
    :ivar abilities: The entity's abilities or actions.
    :ivar source: The source type of the entity.
    :ivar raw: The raw data dictionary.
    """

    def __init__(self, name, entity_type, stats=None, abilities=None, source="monster", raw_data=None):
        """
        Initialize a RulebookEntity.

        :param name: The name of the entity.
        :type name: str
        :param entity_type: The type/category of the entity.
        :type entity_type: str
        :param stats: The entity's statistics.
        :type stats: dict, optional
        :param abilities: The entity's abilities or actions.
        :type abilities: list, optional
        :param source: The source type of the entity.
        :type source: str, optional
        :param raw_data: The raw data dictionary.
        :type raw_data: dict, optional
        """
        self.name = name
        self.entity_type = entity_type  # monster, npc, spell, item, etc.
        self.stats = stats or {}
        self.abilities = abilities or []
        self.source = source  # e.g. "monster" or "spell"
        self.raw = raw_data or {}

    @classmethod
    def from_monster(cls, data: dict):
        """
        Create a RulebookEntity from a monster data dictionary, with heuristics for categorization.

        :param data: The monster data dictionary.
        :type data: dict
        :return: A RulebookEntity instance.
        :rtype: RulebookEntity
        """
        # --- Heuristic for smarter categorization ---
        m_type = data.get("type", "").lower()
        m_subtype = (data.get("subtype") or "").lower()
        m_name = data.get("name", "").lower()

        if "npc" in m_name or (m_type == "humanoid" and "commoner" in m_name):
            entity_type = "npc"
        elif m_type in {"beast", "dragon", "undead", "aberration", "fiend", "celestial"}:
            entity_type = "enemy"
        elif m_type in {"construct", "ooze", "elemental", "plant"}:
            entity_type = "enemy"
        elif "trap" in m_name:
            entity_type = "trap"
        elif "object" in m_type or "door" in m_name:
            entity_type = "obstacle"
        else:
            entity_type = "enemy"  # fallback

        # --- Extract stats ---
        stats = {
            "hp": data.get("hit_points"),
            "ac": data.get("armor_class")[0]["value"] if data.get("armor_class") else None,
            "speed": data.get("speed", {}).get("walk", "0"),
            "str": data.get("strength"),
            "dex": data.get("dexterity"),
            "con": data.get("constitution"),
            "int": data.get("intelligence"),
            "wis": data.get("wisdom"),
            "cha": data.get("charisma"),
            "proficiency_bonus": data.get("proficiency_bonus"),
            "xp": data.get("xp"),
            "cr": data.get("challenge_rating"),
        }

        # --- Parse abilities ---
        abilities = []
        for sa in data.get("special_abilities", []):
            abilities.append(f"{sa['name']}: {sa['desc']}")
        for action in data.get("actions", []):
            abilities.append(f"{action['name']}: {action['desc']}")

        return cls(
            name=data["name"],
            entity_type=entity_type,
            stats=stats,
            abilities=abilities,
            source="monster",
            raw_data=data
        )

    def to_game_entity(self):
        """
        Converts this RulebookEntity into a GameEntity for use in the game system.

        :return: A GameEntity instance.
        :rtype: GameEntity
        """
        from models.entities.game_entity import GameEntity  # adjust if needed
        return GameEntity(
            name=self.name,
            entity_type=self.entity_type,
            stats=self.stats,
            inventory=self.abilities  # temporary: treat abilities like inventory
        )

    @classmethod
    def from_api(cls, data: dict):
        """
        Creates a RulebookEntity from API data (alias for from_monster).

        :param data: The API data dictionary.
        :type data: dict
        :return: A RulebookEntity instance.
        :rtype: RulebookEntity
        """
        return cls.from_monster(data)

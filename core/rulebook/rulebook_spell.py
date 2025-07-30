# rulebook/spell.py

class RulebookSpell:
    """
    Represents a spell as defined in the rulebook, with all relevant properties.

    :param name: Name of the spell.
    :type name: str
    :param level: Spell level.
    :type level: int
    :param school: School of magic.
    :type school: str
    :param casting_time: Time required to cast the spell.
    :type casting_time: str
    :param duration: Duration of the spell's effect.
    :type duration: str
    :param range_: Range of the spell.
    :type range_: str
    :param damage: Damage mapping by slot level, e.g. {1: "1d8"}.
    :type damage: dict, optional
    :param description: Description of the spell.
    :type description: str, optional
    :param dc: Dictionary with DC info, e.g. {"ability": "WIS", "success": "half"}.
    :type dc: dict, optional
    :param classes: List of classes that can cast the spell.
    :type classes: list, optional
    :param area: Area of effect, e.g. {"type": "sphere", "size": 20}.
    :type area: dict, optional
    :param concentration: Whether the spell requires concentration.
    :type concentration: bool, optional
    :param higher_level: List of effects when cast at higher levels.
    :type higher_level: list, optional
    :param material: Material components required.
    :type material: str, optional
    :param components: List of components (V, S, M).
    :type components: list, optional
    :param raw_data: Raw data from the API or source.
    :type raw_data: dict, optional
    """
    def __init__(self, name, level, school, casting_time, duration, range_, damage=None,
                 description="", dc=None, classes=None, area=None, concentration=False,
                 higher_level=None, material=None, components=None, raw_data=None):
        self.name = name
        self.level = level
        self.school = school
        self.casting_time = casting_time
        self.duration = duration
        self.range = range_
        self.damage = damage or {}  # {slot_level: dice}
        self.description = description
        self.dc = dc  # e.g. {"ability": "WIS", "success": "half"}
        self.classes = classes or []
        self.area = area  # {"type": "sphere", "size": 20}
        self.concentration = concentration
        self.higher_level = higher_level or []
        self.material = material
        self.components = components or []
        self.raw = raw_data or {}

    @classmethod
    def from_api(cls, data):
        """
        Create a RulebookSpell instance from API data.

        :param data: Dictionary containing spell data from the API.
        :type data: dict
        :return: RulebookSpell instance populated with API data.
        :rtype: RulebookSpell
        """
        damage = data.get("damage", {}).get("damage_at_slot_level", {})
        if isinstance(damage, dict):
            damage = {int(k): v for k, v in damage.items()}

        return cls(
            name=data["name"],
            level=data["level"],
            school=data["school"]["name"],
            casting_time=data["casting_time"],
            duration=data["duration"],
            range_=data["range"],
            damage=damage,
            description="\n".join(data.get("desc", [])),
            dc={
                "ability": data["dc"]["dc_type"]["name"],
                "success": data["dc"]["dc_success"]
            } if data.get("dc") else None,
            classes=[cls_["name"] for cls_ in data.get("classes", [])],
            area=data.get("area_of_effect"),
            concentration=data.get("concentration", False),
            higher_level=data.get("higher_level", []),
            material=data.get("material"),
            components=data.get("components"),
            raw_data=data
        )

    def to_spell(self):
        """
        Convert this RulebookSpell to a Spell instance from the models module.

        :return: Spell instance with mapped properties.
        :rtype: Spell
        """
        from models.spell import Spell
        # Build payloads
        damage_payload = (
            {"type": self.dc["ability"].lower(), "amount": self.damage.get(self.level)}
            if self.damage else None
        )
        effect_payload = (
            {"type": "buff" if self.dc is None else "debuff", "details": self.description}
            if not self.damage else None
        )
        # Construct Spell with correct signature:
        return Spell(
            self.name,
            interrupt_difficulty=0,
            cast_priority="normal",
            level=self.level,
            school=self.school,
            casting_time=self.casting_time,
            range=self.range,            # <— use `range=`, not `range_=`
            components=self.components,
            duration=self.duration,
            description=self.description,
            damage=damage_payload,
            effect=effect_payload,
            reaction_mode="after"
        )

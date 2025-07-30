import pytest

from core.rulebook.rulebook_spell import RulebookSpell
from models.spell import Spell

@pytest.fixture
def sample_api_data():
    return {
        "name": "Magic Missile",
        "level": 2,
        "school": {"name": "Evocation"},
        "casting_time": "1 action",
        "duration": "Instantaneous",
        "range": "120 feet",
        "damage": {"damage_at_slot_level": {"1": "3d4+3", "2": "4d4+4"}},
        "desc": ["Line one.", "Line two."],
        "dc": {"dc_type": {"name": "Wisdom"}, "dc_success": "half"},
        "classes": [{"name": "Wizard"}, {"name": "Sorcerer"}],
        "area_of_effect": {"type": "sphere", "size": 15},
        "concentration": True,
        "higher_level": [{"extra": "data"}],
        "material": "A bit of fleece",
        "components": ["V", "S", "M"],
        # include raw_data extra fields
        "other": "value"
    }


def test_from_api_parses_fields(sample_api_data):
    spell = RulebookSpell.from_api(sample_api_data)
    # Basic fields
    assert spell.name == "Magic Missile"
    assert spell.level == 2
    assert spell.school == "Evocation"
    assert spell.casting_time == "1 action"
    assert spell.duration == "Instantaneous"
    assert spell.range == "120 feet"
    # Damage mapping keys to ints
    assert isinstance(spell.damage, dict)
    assert spell.damage == {1: "3d4+3", 2: "4d4+4"}
    # Description joined
    assert spell.description == "Line one.\nLine two."
    # DC mapping
    assert spell.dc == {"ability": "Wisdom", "success": "half"}
    # Classes list
    assert spell.classes == ["Wizard", "Sorcerer"]
    # Area, concentration, higher_level, material, components, raw
    assert spell.area == {"type": "sphere", "size": 15}
    assert spell.concentration is True
    assert spell.higher_level == [{"extra": "data"}]
    assert spell.material == "A bit of fleece"
    assert spell.components == ["V", "S", "M"]
    # Raw data retains extra fields
    assert spell.raw.get("other") == "value"

@ pytest.mark.parametrize("damage_dict, dc_value, expected_damage, expected_effect", [
    # Case with damage and a DC: effect should be None
    ({1: "2d6"}, {"ability": "Wisdom", "success": "half"}, {"type": "wisdom", "amount": "2d6"}, None),
    # Case without damage: damage None, effect present
    ({}, None, None, {"type": "buff", "details": "Desc text"}),
])
def test_to_spell_maps_damage_and_effect(damage_dict, dc_value, expected_damage, expected_effect):
    # Construct a minimal RulebookSpell
    rb = RulebookSpell(
        name="TestSpell",
        level=1,
        school="Illusion",
        casting_time="1 min",
        duration="1 hour",
        range_="60 feet",
        damage=damage_dict,
        description="Desc text",
        dc=dc_value,
        classes=[],
        area=None,
        concentration=False,
        higher_level=None,
        material=None,
        components=["V"],
        raw_data={}
    )
    sp = rb.to_spell()

    # Verify Spell instance
    assert isinstance(sp, Spell)

    # Check damage payload
    assert sp.damage == expected_damage
    # Check effect payload
    assert sp.effect == expected_effect

import pytest

from core.rulebook.rulebook_entity import RulebookEntity
from models.entities.game_entity import GameEntity

# Helper to build a minimal monster payload
def make_monster(name, m_type, subtype=None, hp=10, ac_value=12, speed_walk="30 ft",
                 strength=14, dexterity=12, constitution=13,
                 intelligence=10, wisdom=8, charisma=6,
                 proficiency_bonus=2, xp=100, cr=0.25,
                 special_abilities=None, actions=None):
    return {
        "name": name,
        "type": m_type,
        "subtype": subtype,
        "hit_points": hp,
        "armor_class": [{"value": ac_value}],
        "speed": {"walk": speed_walk},
        "strength": strength,
        "dexterity": dexterity,
        "constitution": constitution,
        "intelligence": intelligence,
        "wisdom": wisdom,
        "charisma": charisma,
        "proficiency_bonus": proficiency_bonus,
        "xp": xp,
        "challenge_rating": cr,
        "special_abilities": special_abilities or [],
        "actions": actions or []
    }


@pytest.mark.parametrize("name,m_type,expected_entity_type", [
    # NPC detection: name contains "npc"
    ("Village NPC Guard", "humanoid", "npc"),
    # Humanoid commoner → NPC
    ("Commoner", "humanoid", "npc"),
    # Beasts/dragons/etc. → enemy
    ("Forest Bear", "beast", "enemy"),
    ("Young Dragon", "dragon", "enemy"),
    # Constructs/oozes/etc. → enemy
    ("Living Statue", "construct", "enemy"),
    # Trap detection by name
    ("Spike Trap", "trap", "trap"),
    # Obstacle detection: m_type/object or name contains door
    ("Wooden Door", "object", "obstacle"),
    ("Steel Door", "object", "obstacle"),
    # Fallback
    ("Weird Creature", "unknown", "enemy"),
])
def test_entity_type_classification(name, m_type, expected_entity_type):
    m = make_monster(name=name, m_type=m_type,
                     special_abilities=[{"name":"SA","desc":"Desc"}],
                     actions=[{"name":"Act","desc":"Desc"}])
    re = RulebookEntity.from_monster(m)
    assert re.entity_type == expected_entity_type, f"{name}/{m_type} → {re.entity_type}"
    # maps name and raw_data back
    assert re.name == name
    assert re.raw == m


def test_stats_extraction_and_abilities_combined():
    special = [{"name": "Invisibility", "desc": "Turns invisible"}]
    acts    = [{"name": "Bite",        "desc": "Deals damage"}]
    raw = make_monster(
        name="Shadow Beast",
        m_type="beast",
        hp=42,
        ac_value=15,
        speed_walk="40 ft",
        strength=18,
        dexterity=14,
        constitution=16,
        intelligence=6,
        wisdom=12,
        charisma=8,
        proficiency_bonus=3,
        xp=200,
        cr=1,
        special_abilities=special,
        actions=acts
    )
    re = RulebookEntity.from_monster(raw)

    # stats dict keys
    expected_stats = {
        "hp": 42,
        "ac": 15,
        "speed": "40 ft",
        "str": 18, "dex": 14, "con": 16,
        "int": 6, "wis": 12, "cha": 8,
        "proficiency_bonus": 3,
        "xp": 200,
        "cr": 1,
    }
    assert re.stats == expected_stats

    # abilities list combines both with "Name: Desc"
    assert "Invisibility: Turns invisible" in re.abilities
    assert "Bite: Deals damage" in re.abilities


def test_to_game_entity_preserves_fields():
    raw = make_monster(
        name="Goblin",
        m_type="humanoid",
        special_abilities=[{"name":"Stealth","desc":"Sneaks"}],
        actions=[{"name":"Scimitar","desc":"Slashes"}]
    )
    re = RulebookEntity.from_monster(raw)
    ge = re.to_game_entity()

    # should be a GameEntity
    assert isinstance(ge, GameEntity)
    # name/type/stats
    assert ge.name == re.name
    assert ge.entity_type == re.entity_type
    assert ge.stats == re.stats
    # In this implementation, abilities are used as inventory:
    assert ge.inventory == re.abilities

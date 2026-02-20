import pytest
from ui.dialogs.stat_block_dialog import StatBlockDialog
from models.entities.game_entity import GameEntity
from models.entities.enemy import Enemy
from models.entities.named_enemy import NamedEnemy


@pytest.fixture
def plain_entity():
    return GameEntity(
        name="Test Entity",
        entity_type="object",
        stats={"STR": 14, "DEX": 10, "CON": 12, "INT": 8, "WIS": 13, "CHA": 11},
        inventory=["Sword", "Shield"],
    )


@pytest.fixture
def enemy_entity():
    return Enemy(
        name="Goblin",
        armor_class=15,
        hp=7,
        stats={"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 8, "CHA": 8},
        saving_throws={"DEX": 4},
        attacks=[{"name": "Scimitar", "to_hit": 4, "damage": "1d6+2 slashing"}],
        speed=30,
        resistances=[],
        immunities=[],
        vulnerabilities=[],
        condition_immunities=[],
        challenge_rating=0.25,
        xp=50,
        conditions=[],
        initiative=2,
        spells=[],
    )


@pytest.fixture
def named_enemy_entity():
    return NamedEnemy(
        name="Ancient Red Dragon",
        armor_class=22,
        hp=546,
        stats={"STR": 30, "DEX": 10, "CON": 29, "INT": 18, "WIS": 15, "CHA": 23},
        saving_throws={"DEX": 7, "CON": 16, "WIS": 9, "CHA": 13},
        attacks=[
            {"name": "Bite", "to_hit": 17, "damage": "2d10+10 piercing"},
            {"name": "Claw", "to_hit": 17, "damage": "2d6+10 slashing"},
        ],
        speed=40,
        resistances=[],
        immunities=["fire"],
        vulnerabilities=[],
        condition_immunities=["Frightened"],
        challenge_rating=24,
        xp=62000,
        conditions=[],
        initiative=0,
        spells=[],
        backstory="The terror of the Burning Peaks.",
        legendary_actions=[
            {"name": "Wing Attack", "description": "The dragon beats its wings."}
        ],
        lair_actions=[{"description": "Magma erupts from the ground."}],
        regional_effects=[{"description": "The land is scorched for miles."}],
        spellcasting_ability={"ability": "CHA"},
        phases=[],
    )


def test_stat_block_creates_for_plain_entity(qapp, plain_entity):
    dlg = StatBlockDialog(plain_entity)
    html = dlg.browser.toHtml()
    assert "Test Entity" in html
    assert "object" in html
    # Ability scores should appear
    assert "STR" in html
    assert "DEX" in html
    # Inventory should appear
    assert "Sword" in html
    assert "Shield" in html


def test_stat_block_creates_for_enemy(qapp, enemy_entity):
    dlg = StatBlockDialog(enemy_entity)
    html = dlg.browser.toHtml()
    assert "Goblin" in html
    assert "15" in html  # AC
    assert "Scimitar" in html  # Attack name
    assert "1d6+2 slashing" in html
    assert "0.25" in html  # CR


def test_stat_block_creates_for_named_enemy(qapp, named_enemy_entity):
    dlg = StatBlockDialog(named_enemy_entity)
    html = dlg.browser.toHtml()
    assert "Ancient Red Dragon" in html
    assert "546" in html  # HP
    assert "Legendary Actions" in html
    assert "Wing Attack" in html
    assert "Lair Actions" in html
    assert "Magma erupts" in html
    assert "Regional Effects" in html
    assert "scorched" in html
    assert "Burning Peaks" in html  # backstory


def test_stat_block_ability_modifier(qapp):
    assert StatBlockDialog._modifier(10) == "+0"
    assert StatBlockDialog._modifier(14) == "+2"
    assert StatBlockDialog._modifier(8) == "-1"
    assert StatBlockDialog._modifier(20) == "+5"
    assert StatBlockDialog._modifier(1) == "-5"


def test_stat_block_with_empty_entity(qapp):
    entity = GameEntity(name="Empty", entity_type="thing")
    dlg = StatBlockDialog(entity)
    html = dlg.browser.toHtml()
    assert "Empty" in html
    assert "thing" in html


def test_stat_block_window_title(qapp, enemy_entity):
    dlg = StatBlockDialog(enemy_entity)
    assert "Goblin" in dlg.windowTitle()


def test_stat_block_resistances_immunities(qapp):
    enemy = Enemy(
        name="Elemental",
        armor_class=12,
        hp=50,
        stats={"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10},
        saving_throws={},
        attacks=[],
        speed=30,
        resistances=["fire", "cold"],
        immunities=["poison"],
        vulnerabilities=["lightning"],
        condition_immunities=["Paralyzed"],
        challenge_rating=3,
        xp=700,
        conditions=[],
        initiative=0,
        spells=[],
    )
    dlg = StatBlockDialog(enemy)
    html = dlg.browser.toHtml()
    assert "fire" in html
    assert "cold" in html
    assert "poison" in html
    assert "lightning" in html
    assert "Paralyzed" in html

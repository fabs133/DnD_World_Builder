"""Tests for GameState immutable snapshots."""

import pytest
from core.engine.game_state import GameState, EntitySnapshot, TileSnapshot, _infer_faction
from models.game_master import Gamemaster
from models.entities.game_entity import GameEntity


class SimpleEntity:
    """Minimal entity for testing without DB or trigger dependencies."""

    def __init__(self, name, entity_type="player", hp=10, armor_class=12,
                 stats=None, speed=30, conditions=None, position=(0, 0)):
        self.name = name
        self.entity_type = entity_type
        self.hp = hp
        self.armor_class = armor_class
        self.stats = stats or {"Dexterity": 14, "max_hp": hp}
        self.speed = speed
        self.conditions = conditions or []
        self.position = position
        self.initiative = 0
        self.triggers = []


class TestEntitySnapshot:
    def test_frozen(self):
        snap = EntitySnapshot(
            name="Test", entity_type="player", hp=10, max_hp=10,
            armor_class=12, position=(1, 2), conditions=(), stats={},
            speed=30, faction="player", is_alive=True,
        )
        with pytest.raises(AttributeError):
            snap.hp = 5

    def test_basic_fields(self):
        snap = EntitySnapshot(
            name="Fighter", entity_type="player", hp=20, max_hp=25,
            armor_class=16, position=(3, 4), conditions=("poisoned",),
            stats={"Strength": 18}, speed=30, faction="player", is_alive=True,
        )
        assert snap.name == "Fighter"
        assert snap.hp == 20
        assert snap.max_hp == 25
        assert snap.armor_class == 16
        assert snap.position == (3, 4)
        assert "poisoned" in snap.conditions


class TestGameState:
    def _make_state(self):
        e1 = EntitySnapshot(
            name="Fighter", entity_type="player", hp=20, max_hp=20,
            armor_class=16, position=(0, 0), conditions=(), stats={},
            speed=30, faction="player", is_alive=True,
        )
        e2 = EntitySnapshot(
            name="Goblin", entity_type="enemy", hp=7, max_hp=7,
            armor_class=13, position=(1, 1), conditions=(), stats={},
            speed=30, faction="enemy", is_alive=True,
        )
        e3 = EntitySnapshot(
            name="Cleric", entity_type="player", hp=0, max_hp=15,
            armor_class=14, position=(0, 1), conditions=(), stats={},
            speed=30, faction="player", is_alive=False,
        )
        return GameState(
            round_number=1,
            current_entity_name="Fighter",
            entities=(e1, e2, e3),
            initiative_order=("Fighter", "Goblin", "Cleric"),
            world_width=5, world_height=5, tile_type="square",
        )

    def test_get_entity(self):
        state = self._make_state()
        assert state.get_entity("Fighter").hp == 20
        assert state.get_entity("Missing") is None

    def test_get_enemies_of(self):
        state = self._make_state()
        enemies = state.get_enemies_of("Fighter")
        assert len(enemies) == 1
        assert enemies[0].name == "Goblin"

    def test_get_allies_of(self):
        state = self._make_state()
        # Cleric is dead, so only living allies returned
        allies = state.get_allies_of("Fighter")
        assert len(allies) == 0  # Cleric is not alive

    def test_get_entities_at(self):
        state = self._make_state()
        at_origin = state.get_entities_at(0, 0)
        assert len(at_origin) == 1
        assert at_origin[0].name == "Fighter"

    def test_frozen(self):
        state = self._make_state()
        with pytest.raises(AttributeError):
            state.round_number = 2

    def test_from_gamemaster(self):
        gm = Gamemaster()
        # Expand the default 1x1 world to fit our entities
        from models.world.world import World
        gm.world = World(
            world_version=1, width=5, height=5, tile_type="square",
            description="", map_data={}, time_of_day="", weather_conditions="",
        )
        gm.world_tile_manager = gm.world.tile_manager
        e1 = SimpleEntity("Warrior", "player", hp=25, position=(1, 0))
        e2 = SimpleEntity("Orc", "enemy", hp=15, armor_class=11, position=(2, 0))
        gm.game_entities = [e1, e2]
        gm.world_tile_manager.place_entity(e1, 1, 0)
        gm.world_tile_manager.place_entity(e2, 2, 0)

        state = GameState.from_gamemaster(
            gm, round_number=2, current_entity_name="Warrior",
            initiative_order=["Warrior", "Orc"], seed=42,
        )
        assert state.round_number == 2
        assert state.current_entity_name == "Warrior"
        assert len(state.entities) == 2
        warrior = state.get_entity("Warrior")
        assert warrior.hp == 25
        assert warrior.faction == "player"
        orc = state.get_entity("Orc")
        assert orc.faction == "enemy"


class TestInferFaction:
    def test_player_type(self):
        e = SimpleEntity("A", "player")
        assert _infer_faction(e) == "player"

    def test_enemy_type(self):
        e = SimpleEntity("B", "enemy")
        assert _infer_faction(e) == "enemy"

    def test_npc_type(self):
        e = SimpleEntity("C", "npc")
        assert _infer_faction(e) == "neutral"

    def test_explicit_faction(self):
        e = SimpleEntity("D", "player")
        e.faction = "rebel"
        assert _infer_faction(e) == "rebel"

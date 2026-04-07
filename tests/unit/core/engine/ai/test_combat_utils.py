"""Tests for shared AI combat utility functions."""

import pytest

from core.engine.ai.combat_utils import (
    are_allies,
    find_weakest_target,
    get_actor,
    get_personality,
    get_enemies,
)
from core.engine.game_state import GameState, EntitySnapshot
from models.ai.personality import EntityPersonality
from models.ai.alignment import Alignment


def _snap(name, etype, hp, max_hp, pos, alive=True):
    return EntitySnapshot(
        name=name, entity_type=etype, hp=hp, max_hp=max_hp,
        armor_class=12, position=pos, conditions=(), stats={},
        speed=30, faction=etype, is_alive=alive,
    )


def _state(snaps):
    return GameState(
        round_number=1, current_entity_name=snaps[0].name,
        entities=tuple(snaps),
        initiative_order=tuple(s.name for s in snaps),
        world_width=5, world_height=5, tile_type="square",
    )


class TestAreAllies:
    def test_players_are_allies(self):
        assert are_allies("player", "ally") is True
        assert are_allies("player", "companion") is True

    def test_enemies_are_allies(self):
        assert are_allies("enemy", "monster") is True
        assert are_allies("hostile", "enemy") is True

    def test_player_vs_enemy(self):
        assert are_allies("player", "enemy") is False

    def test_unknown_types(self):
        assert are_allies("npc", "player") is False
        assert are_allies("neutral", "enemy") is False


class TestFindWeakestTarget:
    def test_finds_lowest_hp(self):
        state = _state([
            _snap("A", "enemy", 10, 10, (0, 0)),
            _snap("B", "player", 20, 20, (1, 0)),
            _snap("C", "player", 5, 14, (2, 0)),
        ])
        assert find_weakest_target(["B", "C"], state) == "C"

    def test_single_target(self):
        state = _state([
            _snap("A", "enemy", 10, 10, (0, 0)),
            _snap("B", "player", 20, 20, (1, 0)),
        ])
        assert find_weakest_target(["B"], state) == "B"

    def test_returns_first_when_not_in_state(self):
        state = _state([_snap("A", "enemy", 10, 10, (0, 0))])
        assert find_weakest_target(["X", "Y"], state) == "X"


class TestGetActor:
    def test_returns_entity_from_dict(self):
        class FakeEntity:
            name = "Hero"
        entity = FakeEntity()
        result = get_actor("Hero", {"Hero": entity})
        assert result is entity

    def test_returns_stub_for_missing(self):
        result = get_actor("Missing", {})
        assert result.name == "Missing"
        assert result.entity_type == "creature"
        assert result.hp == 10

    def test_stub_has_required_attributes(self):
        stub = get_actor("Test", {})
        assert hasattr(stub, "name")
        assert hasattr(stub, "entity_type")
        assert hasattr(stub, "hp")
        assert hasattr(stub, "max_hp")
        assert hasattr(stub, "position")
        assert hasattr(stub, "personality")


class TestGetPersonality:
    def test_returns_actor_personality(self):
        personality = EntityPersonality(Alignment.CHAOTIC_EVIL)

        class FakeActor:
            pass
        actor = FakeActor()
        actor.personality = personality

        default = EntityPersonality(Alignment.TRUE_NEUTRAL)
        assert get_personality(actor, default) is personality

    def test_returns_default_when_none(self):
        class FakeActor:
            personality = None
        default = EntityPersonality(Alignment.TRUE_NEUTRAL)
        assert get_personality(FakeActor(), default) is default

    def test_returns_default_when_no_attribute(self):
        default = EntityPersonality(Alignment.TRUE_NEUTRAL)
        assert get_personality(object(), default) is default


class TestGetEnemies:
    def test_returns_enemies_of_player(self):
        state = _state([
            _snap("Hero", "player", 20, 20, (0, 0)),
            _snap("Goblin", "enemy", 7, 7, (1, 0)),
            _snap("Ally", "companion", 15, 15, (2, 0)),
        ])
        enemies = get_enemies("Hero", "player", state)
        assert len(enemies) == 1
        assert enemies[0].name == "Goblin"

    def test_excludes_dead(self):
        state = _state([
            _snap("Hero", "player", 20, 20, (0, 0)),
            _snap("Goblin", "enemy", 0, 7, (1, 0), alive=False),
        ])
        enemies = get_enemies("Hero", "player", state)
        assert len(enemies) == 0

    def test_excludes_self(self):
        state = _state([
            _snap("Goblin", "enemy", 7, 7, (0, 0)),
        ])
        enemies = get_enemies("Goblin", "enemy", state)
        assert len(enemies) == 0

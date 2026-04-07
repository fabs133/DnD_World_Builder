"""Tests for InfoFilter role-based visibility."""

import pytest
from core.engine.info_filter import InfoFilter
from core.engine.play_state import PlayerRole


class MockEntity:
    def __init__(self, name, entity_type="enemy", hp=10):
        self.name = name
        self.entity_type = entity_type
        self.hp = hp


class TestHealthCategory:
    def test_full_hp(self):
        assert InfoFilter.health_category(100, 100) == "healthy"

    def test_above_75_percent(self):
        assert InfoFilter.health_category(76, 100) == "healthy"

    def test_at_75_percent(self):
        assert InfoFilter.health_category(75, 100) == "wounded"

    def test_above_50_percent(self):
        assert InfoFilter.health_category(51, 100) == "wounded"

    def test_at_50_percent(self):
        assert InfoFilter.health_category(50, 100) == "bloodied"

    def test_above_25_percent(self):
        assert InfoFilter.health_category(26, 100) == "bloodied"

    def test_at_25_percent(self):
        assert InfoFilter.health_category(25, 100) == "near_death"

    def test_at_1_hp(self):
        assert InfoFilter.health_category(1, 100) == "near_death"

    def test_at_0_hp(self):
        assert InfoFilter.health_category(0, 100) == "unconscious"

    def test_zero_max_hp(self):
        assert InfoFilter.health_category(0, 0) == "unconscious"


class TestCanSeeHp:
    def test_dm_sees_all(self):
        f = InfoFilter(PlayerRole.DM, "Fighter", frozenset({"Fighter"}))
        assert f.can_see_hp("Fighter") is True
        assert f.can_see_hp("Goblin") is True

    def test_spectator_sees_all(self):
        f = InfoFilter(PlayerRole.SPECTATOR, None, frozenset({"Fighter"}))
        assert f.can_see_hp("Goblin") is True

    def test_player_sees_party(self):
        f = InfoFilter(PlayerRole.PLAYER, "Fighter", frozenset({"Fighter", "Rogue"}))
        assert f.can_see_hp("Fighter") is True
        assert f.can_see_hp("Rogue") is True

    def test_player_cannot_see_enemy(self):
        f = InfoFilter(PlayerRole.PLAYER, "Fighter", frozenset({"Fighter"}))
        assert f.can_see_hp("Goblin") is False


class TestShouldFog:
    def test_player_has_fog(self):
        f = InfoFilter(PlayerRole.PLAYER)
        assert f.should_fog() is True

    def test_dm_no_fog(self):
        f = InfoFilter(PlayerRole.DM)
        assert f.should_fog() is False

    def test_spectator_has_fog(self):
        f = InfoFilter(PlayerRole.SPECTATOR)
        assert f.should_fog() is True


class TestCanControl:
    def test_player_controls_own(self):
        f = InfoFilter(PlayerRole.PLAYER, "Fighter")
        assert f.can_control("Fighter") is True
        assert f.can_control("Goblin") is False

    def test_dm_controls_all(self):
        f = InfoFilter(PlayerRole.DM)
        assert f.can_control("Fighter") is True
        assert f.can_control("Goblin") is True

    def test_spectator_controls_none(self):
        f = InfoFilter(PlayerRole.SPECTATOR)
        assert f.can_control("Fighter") is False


class TestGetVisionEntities:
    def test_player_only_sees_own(self):
        entities = [MockEntity("Fighter", "player"), MockEntity("Rogue", "player"),
                    MockEntity("Goblin", "enemy")]
        f = InfoFilter(PlayerRole.PLAYER, "Fighter")
        result = f.get_vision_entities(entities)
        assert len(result) == 1
        assert result[0].name == "Fighter"

    def test_dm_returns_empty(self):
        entities = [MockEntity("Fighter", "player")]
        f = InfoFilter(PlayerRole.DM)
        result = f.get_vision_entities(entities)
        assert result == []

    def test_spectator_returns_all_players(self):
        entities = [MockEntity("Fighter", "player"), MockEntity("Rogue", "player"),
                    MockEntity("Goblin", "enemy")]
        f = InfoFilter(PlayerRole.SPECTATOR)
        result = f.get_vision_entities(entities)
        assert len(result) == 2


class TestInitiativeRole:
    def test_player_returns_player(self):
        f = InfoFilter(PlayerRole.PLAYER)
        assert f.initiative_role() == "player"

    def test_dm_returns_dm(self):
        f = InfoFilter(PlayerRole.DM)
        assert f.initiative_role() == "dm"

    def test_spectator_returns_dm(self):
        f = InfoFilter(PlayerRole.SPECTATOR)
        assert f.initiative_role() == "dm"


class TestCanSeeStats:

    def test_dm_sees_all(self):
        f = InfoFilter(PlayerRole.DM)
        assert f.can_see_stats("Goblin") is True
        assert f.can_see_stats("Fighter") is True

    def test_player_sees_own_only(self):
        f = InfoFilter(PlayerRole.PLAYER, "Fighter", frozenset(["Fighter", "Wizard"]))
        assert f.can_see_stats("Fighter") is True
        assert f.can_see_stats("Wizard") is False
        assert f.can_see_stats("Goblin") is False

    def test_spectator_sees_party(self):
        f = InfoFilter(PlayerRole.SPECTATOR, party_names=frozenset(["Fighter", "Wizard"]))
        assert f.can_see_stats("Fighter") is True
        assert f.can_see_stats("Wizard") is True
        assert f.can_see_stats("Goblin") is False

"""Tests for Gamemaster combat encounter management."""

import pytest
from unittest.mock import MagicMock

from core.events import COMBAT_STARTED
from core.gameCreation.event_bus import EventBus
from models.game_master import Gamemaster
from models.entities.game_entity import GameEntity
from models.combat.encounter_template import EncounterTemplate, EnemySpawn


@pytest.fixture(autouse=True)
def reset_bus():
    EventBus.reset()
    yield
    EventBus.reset()


@pytest.fixture
def gamemaster():
    return Gamemaster()


@pytest.fixture
def template():
    return EncounterTemplate(
        template_id="test_fight",
        name="Test Fight",
        grid_width=5,
        grid_height=5,
        enemy_spawns=[EnemySpawn(position=(4, 0), creature_index="goblin", count=2)],
        player_spawn_zone=[(0, 4)],
    )


class TestGamemasterCombat:

    def test_register_encounter(self, gamemaster, template):
        gamemaster.register_encounter(template)
        assert "test_fight" in gamemaster.encounter_templates

    def test_start_combat_creates_orchestrator(self, gamemaster, template):
        gamemaster.register_encounter(template)
        player = GameEntity("Hero", "player", stats={"hp": 20})
        orch = gamemaster.start_combat("test_fight", [player])
        assert gamemaster.active_combat is orch
        assert orch.instance is not None

    def test_start_combat_emits_event(self, gamemaster, template):
        events = []
        EventBus.subscribe(COMBAT_STARTED, lambda d: events.append(d))

        gamemaster.register_encounter(template)
        player = GameEntity("Hero", "player", stats={"hp": 20})
        gamemaster.start_combat("test_fight", [player])

        assert len(events) == 1

    def test_end_combat_clears_active(self, gamemaster, template):
        gamemaster.register_encounter(template)
        player = GameEntity("Hero", "player", stats={"hp": 20})
        gamemaster.start_combat("test_fight", [player])
        gamemaster.end_combat()
        assert gamemaster.active_combat is None

    def test_start_combat_unknown_template_raises(self, gamemaster):
        with pytest.raises(ValueError):
            gamemaster.start_combat("nonexistent", [])

"""Fixtures for behavioral tests."""

import pytest

from core.testing.behavioral.harness import (
    BehavioralTestHarness,
    ScenarioConfig,
    HarnessConfig,
)


@pytest.fixture
def quick_harness():
    """Fast harness for CI — 10 runs, mock AI."""
    def _create(scenario: ScenarioConfig):
        config = HarnessConfig(runs=10, parallel_workers=4)
        return BehavioralTestHarness(scenario, config)
    return _create


@pytest.fixture
def thorough_harness():
    """Thorough harness — 100 runs, mock AI."""
    def _create(scenario: ScenarioConfig):
        config = HarnessConfig(runs=100, parallel_workers=4)
        return BehavioralTestHarness(scenario, config)
    return _create


@pytest.fixture
def goblin_ambush_scenario():
    """Classic scenario: 2 players vs 4 goblins in mixed alignments."""
    return ScenarioConfig(
        name="goblin_ambush",
        description="2 adventurers vs 4 goblins in a ruined temple",
        entities=[
            {"name": "Fighter", "type": "player", "hp": 28,
             "alignment": "lawful_good", "position": [2, 5],
             "armor_class": 16, "dex": 12},
            {"name": "Wizard", "type": "player", "hp": 14,
             "alignment": "chaotic_good", "position": [3, 5],
             "armor_class": 11, "dex": 14},
            {"name": "Goblin_1", "type": "enemy", "hp": 7,
             "alignment": "neutral_evil", "position": [7, 3],
             "armor_class": 13, "dex": 14},
            {"name": "Goblin_2", "type": "enemy", "hp": 7,
             "alignment": "neutral_evil", "position": [7, 7],
             "armor_class": 13, "dex": 14},
            {"name": "Goblin_3", "type": "enemy", "hp": 7,
             "alignment": "chaotic_evil", "position": [8, 5],
             "armor_class": 13, "dex": 14,
             "trait": "Cackles maniacally"},
            {"name": "Shaman", "type": "enemy", "hp": 12,
             "alignment": "lawful_evil", "position": [9, 5],
             "armor_class": 14, "dex": 12,
             "trait": "Commands the others"},
        ],
        map_size=(10, 10),
        max_rounds=15,
    )


@pytest.fixture
def duel_scenario():
    """Simple 1v1 for focused alignment testing."""
    def _create(player_alignment: str, enemy_alignment: str):
        return ScenarioConfig(
            name=f"duel_{player_alignment}_vs_{enemy_alignment}",
            entities=[
                {"name": "Player", "type": "player", "hp": 20,
                 "alignment": player_alignment, "position": [0, 0]},
                {"name": "Enemy", "type": "enemy", "hp": 20,
                 "alignment": enemy_alignment, "position": [4, 4]},
            ],
            map_size=(5, 5),
            max_rounds=10,
        )
    return _create

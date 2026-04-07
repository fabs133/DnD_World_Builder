"""Play session runner — bridges map.json scenario data to a live GameSession.

Loads entities from tile data, creates a Gamemaster, assigns adapters
(UIInputAdapter for player-controlled entities, HeuristicAIAdapter for
enemies/NPCs), and drives the turn loop.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from core.logger import app_logger
from models.entities.game_entity import GameEntity
from models.game_master import Gamemaster
from core.engine.game_session import GameSession, GameSessionResult
from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
from core.engine.input_adapter import InputAdapter
from core.engine.entity_utils import disambiguate_names, filter_combatants


@dataclass
class PlayConfig:
    """Configuration for a play session."""
    seed: int = 42
    max_rounds: int = 100
    player_entity_names: list[str] = field(default_factory=list)
    role: str = "player"                # "player", "dm", "spectator"
    controlled_character: str = ""      # Entity name the player controls


def default_test_party() -> list[dict]:
    """Create a default party of 4 level-3 adventurers.

    Returns entity dicts ready for GameEntity.from_dict().
    """
    return [
        {
            "name": "Fighter",
            "entity_type": "player",
            "stats": {"str": 16, "dex": 12, "con": 14, "int": 10, "wis": 12, "cha": 8,
                       "ac": 16, "hp": 28, "max_hp": 28, "speed": 30},
            "hp": 28, "max_hp": 28,
            "inventory": ["Longsword", "Shield"], "triggers": [], "conditions": [],
        },
        {
            "name": "Rogue",
            "entity_type": "player",
            "stats": {"str": 10, "dex": 16, "con": 12, "int": 13, "wis": 10, "cha": 14,
                       "ac": 14, "hp": 24, "max_hp": 24, "speed": 30},
            "hp": 24, "max_hp": 24,
            "inventory": ["Shortsword", "Shortbow"], "triggers": [], "conditions": [],
        },
        {
            "name": "Wizard",
            "entity_type": "player",
            "stats": {"str": 8, "dex": 14, "con": 12, "int": 17, "wis": 13, "cha": 10,
                       "ac": 12, "hp": 18, "max_hp": 18, "speed": 30},
            "hp": 18, "max_hp": 18,
            "inventory": ["Quarterstaff", "Spellbook"], "triggers": [], "conditions": [],
        },
        {
            "name": "Cleric",
            "entity_type": "player",
            "stats": {"str": 14, "dex": 10, "con": 14, "int": 10, "wis": 16, "cha": 12,
                       "ac": 16, "hp": 24, "max_hp": 24, "speed": 30},
            "hp": 24, "max_hp": 24,
            "inventory": ["Mace", "Shield", "Holy Symbol"], "triggers": [], "conditions": [],
        },
    ]


def extract_entities_from_tiles(
    tile_dicts: list[dict],
) -> tuple[list[GameEntity], tuple[int, int]]:
    """Extract all entities and START_ZONE position from tile data.

    Applies name disambiguation. Does NOT filter combatants — the caller
    decides what subset to use.

    Returns:
        (all_entities, start_position)
    """
    all_entities: list[GameEntity] = []
    start_position = (0, 0)

    for tile in tile_dicts:
        tile_pos = tuple(tile.get("position", [0, 0]))
        tags = tile.get("tags", [])

        if "START_ZONE" in tags:
            start_position = tile_pos

        for edict in tile.get("entities", []):
            entity = GameEntity.from_dict(edict)
            if not entity.position:
                entity.position = tile_pos
            all_entities.append(entity)

    disambiguate_names(all_entities)
    return all_entities, start_position


class PlaySessionRunner:
    """Manages a live play session from scenario data.

    Usage:
        runner = PlaySessionRunner.from_tile_data(tile_dicts, config, ui_adapter)
        # The runner holds a GameSession ready to step through.
        # Call runner.run_one_turn() per turn, or runner.advance_ai_turns()
        # to auto-play AI turns and pause on player turns.
    """

    def __init__(self, entities: list[GameEntity],
                 adapters: dict[str, InputAdapter],
                 config: PlayConfig):
        self._config = config
        self._entities = entities

        gm = Gamemaster()
        for e in entities:
            gm.add_entity(e)

        # Assign positions to entities without one
        for i, e in enumerate(entities):
            if not getattr(e, "position", None):
                e.position = (0, i)

        # Set world dimensions from actual entity positions so the AI
        # knows the valid grid bounds for movement decisions.
        max_row = max_col = 0
        for e in entities:
            pos = getattr(e, "position", (0, 0))
            if pos:
                max_row = max(max_row, pos[0])
                max_col = max(max_col, pos[1])
        gm.world_tile_manager.width = max_row + 2   # +2 for margin
        gm.world_tile_manager.height = max_col + 2

        self._session = GameSession(
            gamemaster=gm,
            adapters=adapters,
            seed=config.seed,
            max_rounds=config.max_rounds,
        )
        self._session.setup(entities)
        self._gm = gm

    @classmethod
    def from_entities(cls, all_entities: list[GameEntity],
                      config: PlayConfig,
                      player_adapter: InputAdapter) -> PlaySessionRunner:
        """Build a play session from pre-extracted entities.

        Use this when entities have already been extracted and disambiguated
        (e.g. during exploration mode). Avoids re-extracting from tile data.
        """
        combatants = filter_combatants(all_entities)

        # Determine which entities the player controls based on role
        players = [e for e in all_entities if e.entity_type == "player"]
        if config.role == "player" and config.controlled_character:
            player_names = [config.controlled_character]
        elif config.role == "spectator":
            player_names = []
        elif config.role == "dm":
            player_names = config.player_entity_names or [e.name for e in players]
        else:
            player_names = config.player_entity_names or [e.name for e in players]

        rng = random.Random(config.seed)
        entities_by_name = {e.name: e for e in combatants}
        adapters: dict[str, InputAdapter] = {}

        for entity in combatants:
            if entity.name in player_names:
                adapters[entity.name] = player_adapter
            else:
                adapters[entity.name] = HeuristicAIAdapter(
                    entities_by_name=entities_by_name,
                    rng=random.Random(rng.randint(0, 2**31)),
                )

        return cls(combatants, adapters, config)

    @classmethod
    def from_tile_data(cls, tile_dicts: list[dict],
                       config: PlayConfig,
                       player_adapter: InputAdapter) -> PlaySessionRunner:
        """Build a play session from map.json tile dicts.

        1. Extracts all entities from tiles
        2. Finds START_ZONE tile for initial placement
        3. If no player entities exist, spawns a default test party
        4. Assigns adapters based on config.role
        """
        all_entities, start_position = extract_entities_from_tiles(tile_dicts)

        # Check if we have player entities
        players = [e for e in all_entities if e.entity_type == "player"]
        enemies = [e for e in all_entities if e.entity_type == "enemy"]

        if not players:
            # Spawn default test party at START_ZONE
            for pdict in default_test_party():
                pe = GameEntity.from_dict(pdict)
                pe.position = start_position
                all_entities.append(pe)
                players.append(pe)
            app_logger.info(f"[Play] Spawned default party at {start_position}")

        if not enemies:
            app_logger.warning("[Play] No enemies found in scenario")

        # Filter to combatants for the turn system (items/traps/obstacles excluded)
        combatants = filter_combatants(all_entities)
        app_logger.info(
            f"[Play] {len(all_entities)} entities total, "
            f"{len(combatants)} combatants in initiative"
        )

        # Determine which entities the player controls based on role
        if config.role == "player" and config.controlled_character:
            player_names = [config.controlled_character]
        elif config.role == "spectator":
            player_names = []  # All AI-controlled
        elif config.role == "dm":
            player_names = config.player_entity_names or [e.name for e in players]
        else:
            player_names = config.player_entity_names or [e.name for e in players]

        # Build adapters only for combatants
        rng = random.Random(config.seed)
        entities_by_name = {e.name: e for e in combatants}
        adapters: dict[str, InputAdapter] = {}

        for entity in combatants:
            if entity.name in player_names:
                adapters[entity.name] = player_adapter
            else:
                adapters[entity.name] = HeuristicAIAdapter(
                    entities_by_name=entities_by_name,
                    rng=random.Random(rng.randint(0, 2**31)),
                )

        return cls(combatants, adapters, config)

    @property
    def session(self) -> GameSession:
        return self._session

    @property
    def entities(self) -> list[GameEntity]:
        return self._entities

    @property
    def is_finished(self) -> bool:
        return self._session.is_finished

    def get_state(self):
        return self._session.get_state()

    def run_one_turn(self):
        """Run a single entity's turn."""
        return self._session.run_one_turn()

    def current_entity_name(self) -> str | None:
        entry = self._session._initiative.current_entity
        return entry.entity_name if entry else None

    def is_player_turn(self) -> bool:
        """Check if the current turn belongs to a player-controlled entity."""
        name = self.current_entity_name()
        if not name:
            return False
        adapter = self._session._adapters.get(name)
        from core.engine.ui_adapter import UIInputAdapter
        return isinstance(adapter, UIInputAdapter)

    def set_adapter(self, entity_name: str, adapter) -> None:
        """Swap the input adapter for an entity mid-session."""
        self._session.set_adapter(entity_name, adapter)

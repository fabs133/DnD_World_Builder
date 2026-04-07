"""Pre-built demo scenario: 2 players vs 3 goblins in a dungeon room."""

from __future__ import annotations

from typing import Any

from models.game_master import Gamemaster
from models.world.world import World
from core.engine.game_session import GameSession
from core.engine.input_adapter import InputAdapter
from core.engine.ai.ai_adapter import AIAdapter
from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
from core.engine.ai.ollama_client import OllamaClient, OllamaConfig
from core.engine.ai import TACTICAL, AGGRESSIVE


class DemoEntity:
    """Simple entity for demo scenarios (no DB or trigger deps)."""

    def __init__(
        self, name: str, entity_type: str, hp: int,
        armor_class: int = 12, speed: int = 30, dex: int = 10,
    ):
        self.name = name
        self.entity_type = entity_type
        self.hp = hp
        self.max_hp = hp
        self.armor_class = armor_class
        self.speed = speed
        self.stats = {"Dexterity": dex, "Strength": 10, "max_hp": hp}
        self.conditions: list[str] = []
        self.position = (0, 0)
        self.initiative = 0
        self.triggers: list = []
        self.inventory: list = []


def build_demo_encounter(
    player_adapters: dict[str, InputAdapter] | None = None,
    seed: int = 42,
    max_rounds: int = 20,
    ollama_config: OllamaConfig | None = None,
    use_heuristic: bool = False,
) -> GameSession:
    """Build a complete demo encounter.

    Creates:
    - 5x5 dungeon room (square grid)
    - 2 fighter characters (players)
    - 3 goblins (enemies, AI-controlled)

    Args:
        player_adapters: Optional dict of entity_name -> InputAdapter for players.
            If not provided, players will also be AI-controlled.
        seed: Random seed for deterministic replay.
        max_rounds: Maximum rounds before the game ends.
        ollama_config: Configuration for the Ollama client.
        use_heuristic: If True, use HeuristicAIAdapter instead of Ollama.

    Returns:
        Configured GameSession ready to run.
    """
    gm = Gamemaster()
    gm.world = World(
        world_version=1, width=5, height=5, tile_type="square",
        description="A crumbling dungeon chamber",
        map_data={}, time_of_day="night", weather_conditions="underground",
    )
    gm.world_tile_manager = gm.world.tile_manager

    # Players
    fighter = DemoEntity("Fighter", "player", hp=28, armor_class=16, dex=12)
    ranger = DemoEntity("Ranger", "player", hp=22, armor_class=14, dex=16)

    # Enemies
    goblin1 = DemoEntity("Goblin_1", "enemy", hp=7, armor_class=13, dex=14)
    goblin2 = DemoEntity("Goblin_2", "enemy", hp=7, armor_class=13, dex=14)
    goblin3 = DemoEntity("Goblin_3", "enemy", hp=10, armor_class=14, dex=12)

    all_entities = [fighter, ranger, goblin1, goblin2, goblin3]
    entities_by_name = {e.name: e for e in all_entities}

    # Place entities on the grid
    gm.world_tile_manager.place_entity(fighter, 0, 2)
    gm.world_tile_manager.place_entity(ranger, 0, 3)
    gm.world_tile_manager.place_entity(goblin1, 4, 1)
    gm.world_tile_manager.place_entity(goblin2, 4, 3)
    gm.world_tile_manager.place_entity(goblin3, 3, 2)

    for entity in all_entities:
        gm.add_entity(entity)

    # Set up AI adapters for goblins (always AI-controlled)
    config = ollama_config or OllamaConfig()
    adapters: dict[str, InputAdapter] = {}

    if use_heuristic:
        # Deterministic heuristic AI — no Ollama dependency
        import random

        rng = random.Random(seed)

        if player_adapters:
            adapters.update(player_adapters)
        else:
            for name in ("Fighter", "Ranger"):
                adapters[name] = HeuristicAIAdapter(
                    entities_by_name=entities_by_name,
                    rng=rng,
                    default_personality=TACTICAL,
                    tile_map=gm.world_tile_manager,
                )
        for name in ("Goblin_1", "Goblin_2", "Goblin_3"):
            adapters[name] = HeuristicAIAdapter(
                entities_by_name=entities_by_name,
                rng=rng,
                default_personality=AGGRESSIVE,
                tile_map=gm.world_tile_manager,
            )
    else:
        # LLM-powered AI via Ollama
        # Player adapters (provided or AI fallback)
        if player_adapters:
            adapters.update(player_adapters)
        else:
            for name in ("Fighter", "Ranger"):
                adapters[name] = AIAdapter(
                    ollama_client=OllamaClient(config),
                    default_personality=TACTICAL,
                    entities_by_name=entities_by_name,
                )

        # Goblin AI adapters
        for name in ("Goblin_1", "Goblin_2", "Goblin_3"):
            adapters[name] = AIAdapter(
                ollama_client=OllamaClient(config),
                default_personality=AGGRESSIVE,
                entities_by_name=entities_by_name,
            )

    return GameSession(
        gm, adapters, seed=seed, max_rounds=max_rounds,
    )

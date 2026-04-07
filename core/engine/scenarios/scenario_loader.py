"""Load YAML scenario definitions into runnable GameSession instances."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Callable

import yaml

from models.game_master import Gamemaster
from models.world.world import World
from models.ai.alignment import Alignment
from models.ai.personality import EntityPersonality
from core.engine.game_session import GameSession, GameSessionResult
from core.engine.game_state import GameState
from core.engine.input_adapter import InputAdapter
from core.engine.action_executor import ActionResult
from core.engine.ai.ai_adapter import AIAdapter
from core.engine.ai.ollama_client import OllamaClient, OllamaConfig
from core.testing.behavioral.harness import BehavioralEntity
from core.testing.behavioral.mock_ai import MockAIAdapter
from core.testing.behavioral.stats import EntityRunStats
from domain.specs.ruleset import Ruleset, RuleInstance


# Maps preset names to EntityPersonality factory methods
PERSONALITY_PRESETS: dict[str, Callable[[], EntityPersonality]] = {
    "goblin_grunt": EntityPersonality.goblin_grunt,
    "goblin_shaman": EntityPersonality.goblin_shaman,
    "orc_berserker": EntityPersonality.orc_berserker,
    "paladin_companion": EntityPersonality.paladin_companion,
    "rogue_companion": EntityPersonality.rogue_companion,
    "undead_minion": EntityPersonality.undead_minion,
}


class ScenarioLoader:
    """Loads a YAML scenario definition and produces a runnable GameSession."""

    def __init__(self, path: str | Path):
        self._path = Path(path)
        with open(self._path) as f:
            self._data: dict[str, Any] = yaml.safe_load(f)

    @property
    def name(self) -> str:
        return self._data.get("name", "Unknown Scenario")

    @property
    def description(self) -> str:
        return self._data.get("description", "")

    @property
    def entity_configs(self) -> list[dict]:
        return self._data.get("entities", [])

    def build_session(
        self,
        mode: str = "mock",
        seed: int = 42,
        max_rounds: int | None = None,
        ollama_config: OllamaConfig | None = None,
        on_round_start: Callable[[GameState], None] | None = None,
        on_turn_start: Callable[[GameState, str], None] | None = None,
        on_action_result: Callable[[ActionResult], None] | None = None,
        on_round_end: Callable[[GameState], None] | None = None,
    ) -> GameSession:
        """Build a GameSession from the scenario definition.

        Args:
            mode: "mock" for MockAIAdapter (instant, deterministic),
                  "ollama" for LLM-backed AI.
            seed: Random seed for deterministic replay.
            max_rounds: Override max_rounds from YAML.
            ollama_config: Ollama configuration (only used if mode="ollama").
            on_round_start: Callback fired at the start of each round.
            on_turn_start: Callback fired at the start of each turn.
            on_action_result: Callback fired after each action.
            on_round_end: Callback fired at the end of each round.

        Returns:
            Configured GameSession ready to run via session.setup() then session.run().
        """
        rng = random.Random(seed)
        map_size = self._data.get("map_size", [10, 10])
        rounds = max_rounds or self._data.get("max_rounds", 20)

        # 1. Create Gamemaster + World
        gm = Gamemaster()
        gm.world = World(
            world_version=1,
            width=map_size[0],
            height=map_size[1],
            tile_type="square",
            description=self.description,
            map_data={},
            time_of_day="",
            weather_conditions="",
        )
        gm.world_tile_manager = gm.world.tile_manager

        # 2. Apply terrain configuration from YAML
        terrain_data = self._data.get("terrain", {})
        for terrain_name, terrain_cfg in terrain_data.items():
            positions = terrain_cfg.get("positions", [])
            cost = terrain_cfg.get("movement_cost")
            blocking = terrain_cfg.get("blocking", False)
            # movement_cost is already in feet (default tile = 5ft)
            feet_cost = cost
            for pos in positions:
                gm.world_tile_manager.set_terrain_config(
                    pos[0], pos[1],
                    movement_cost=feet_cost,
                    blocking=blocking,
                )

            # Parse trigger if present in terrain config
            trigger_cfg = terrain_cfg.get("trigger")
            if trigger_cfg:
                trigger = _create_terrain_trigger(terrain_name, trigger_cfg)
                if trigger:
                    for pos in positions:
                        _attach_trigger_to_tile(gm, trigger, pos)

        # 3. Parse optional rules section
        ruleset = _parse_ruleset(self._data.get("rules"))

        # 4. Create entities (after terrain so placement is on configured tiles)
        entities_by_name: dict[str, BehavioralEntity] = {}
        for cfg in self.entity_configs:
            entity = _create_entity(cfg)
            pos = cfg.get("position", [0, 0])
            gm.world_tile_manager.place_entity(entity, pos[0], pos[1])
            gm.add_entity(entity)
            entities_by_name[entity.name] = entity

        # 5. Create adapters
        adapters = _create_adapters(mode, entities_by_name, rng, ollama_config)

        # 6. Build session
        return GameSession(
            gm,
            adapters,
            seed=seed,
            max_rounds=rounds,
            ruleset=ruleset,
            on_round_start=on_round_start,
            on_turn_start=on_turn_start,
            on_action_result=on_action_result,
            on_round_end=on_round_end,
        )


def _parse_ruleset(rules_data: dict | None) -> Ruleset | None:
    """Parse a ``rules:`` YAML section into a :class:`Ruleset`.

    Returns ``None`` when the section is absent.
    """
    if not rules_data:
        return None

    ruleset = Ruleset(
        ruleset_id=rules_data.get("ruleset_id", "scenario_rules"),
        name=rules_data.get("name", "Scenario Rules"),
        description=rules_data.get("description", ""),
        enforce_base_rules=rules_data.get("enforce_base_rules", True),
    )

    for rule_cfg in rules_data.get("active_rules", []):
        ruleset.add_rule(
            rule_cfg["rule_id"],
            inverted=rule_cfg.get("inverted", False),
            **rule_cfg.get("params", {}),
        )

    return ruleset


def _create_entity(cfg: dict) -> BehavioralEntity:
    """Create a BehavioralEntity from a YAML entity config dict."""
    entity = BehavioralEntity(
        name=cfg["name"],
        entity_type=cfg.get("type", "enemy"),
        hp=cfg.get("hp", 10),
        armor_class=cfg.get("armor_class", 12),
        speed=cfg.get("speed", 30),
        dex=cfg.get("dex", 10),
        position=tuple(cfg.get("position", [0, 0])),
    )

    # Apply personality preset or build from alignment
    preset_name = cfg.get("personality_preset")
    if preset_name and preset_name in PERSONALITY_PRESETS:
        personality = PERSONALITY_PRESETS[preset_name]()
    else:
        alignment_str = cfg.get("alignment", "true neutral")
        alignment = Alignment.from_string(alignment_str.replace("_", " "))
        personality = EntityPersonality(alignment=alignment)

    # Override roleplay traits from YAML
    if cfg.get("trait"):
        personality.trait = cfg["trait"]
    if cfg.get("bond"):
        personality.bond = cfg["bond"]
    if cfg.get("flaw"):
        personality.flaw = cfg["flaw"]

    entity.personality = personality

    # Extract portrait paths from YAML health_states
    portraits_cfg = cfg.get("portraits", {})
    if isinstance(portraits_cfg, dict) and portraits_cfg.get("needed"):
        health_states = portraits_cfg.get("health_states", {})
        for state_name, state_cfg in health_states.items():
            if isinstance(state_cfg, dict):
                output_path = state_cfg.get("output")
                if output_path:
                    entity.portraits[state_name] = output_path
        if "healthy" in entity.portraits:
            entity.image_path = entity.portraits["healthy"]

    return entity


def _create_adapters(
    mode: str,
    entities_by_name: dict[str, Any],
    rng: random.Random,
    ollama_config: OllamaConfig | None,
) -> dict[str, InputAdapter]:
    """Create input adapters for all entities based on mode."""
    if mode == "mock":
        mock = MockAIAdapter(entities_by_name=entities_by_name, rng=rng)
        return {name: mock for name in entities_by_name}

    if mode == "ollama":
        config = ollama_config or OllamaConfig()
        adapters: dict[str, InputAdapter] = {}
        for name, entity in entities_by_name.items():
            personality = getattr(entity, "personality", None)
            adapters[name] = AIAdapter(
                ollama_client=OllamaClient(config),
                default_personality=personality or EntityPersonality(Alignment.TRUE_NEUTRAL),
                entities_by_name=entities_by_name,
            )
        return adapters

    raise ValueError(f"Unknown mode: {mode!r}. Use 'mock' or 'ollama'.")


def _create_terrain_trigger(terrain_name: str, cfg: dict):
    """Create a Trigger from a terrain YAML trigger config.

    :param terrain_name: Name of the terrain section (e.g. ``"trap"``).
    :param cfg: Trigger config dict from YAML.
    :returns: A Trigger instance, or None if config is invalid.
    """
    from core.gameCreation.trigger import Trigger
    from models.flow.condition.condition_list import AlwaysTrue
    from models.flow.reaction.reactions_list import ApplyDamage

    event_type = cfg.get("event_type", "ENTER_TILE")
    # Normalize aliases
    event_map = {"entity_enters": "ENTER_TILE", "on_damage": "ON_DAMAGE"}
    event_type = event_map.get(event_type, event_type.upper())

    condition = AlwaysTrue()

    damage = cfg.get("damage")
    if damage:
        damage_type = cfg.get("effect", "trap")
        # Store dice expression so it's rolled fresh each time the trap fires
        reaction = ApplyDamage(damage_type=damage_type, damage_expr=damage)
    else:
        return None

    return Trigger(
        event_type=event_type,
        condition=condition,
        reaction=reaction,
        label=f"terrain_{terrain_name}_trap",
        source=terrain_name,
    )


def _attach_trigger_to_tile(gm, trigger, pos):
    """Place a trap entity hosting a trigger at the given position.

    :param gm: The Gamemaster instance.
    :param trigger: The Trigger to attach.
    :param pos: ``[x, y]`` position.
    """
    from models.entities.game_entity import GameEntity

    trap_name = f"trap_{pos[0]}_{pos[1]}"
    trap = GameEntity(name=trap_name, entity_type="trap", stats={})
    trap.position = (pos[0], pos[1])
    trap.hp = 1  # traps don't die
    trap.max_hp = 1
    trap.register_trigger(trigger)
    gm.world_tile_manager.place_entity(trap, pos[0], pos[1])

"""Behavioral test harness — runs many mock combat sessions and collects stats."""

from __future__ import annotations

import random
import re
import time
import concurrent.futures
from dataclasses import dataclass, field
from typing import Any, Callable

from models.game_master import Gamemaster
from models.world.world import World
from models.ai.alignment import Alignment
from models.ai.personality import EntityPersonality
from core.engine.game_session import GameSession
from core.engine.input_adapter import InputAdapter
from core.engine.actions.attack_action import AttackAction
from core.testing.behavioral.stats import BehaviorEvent, EntityRunStats, BehaviorStats
from core.testing.behavioral.mock_ai import MockAIAdapter


# ---------------------------------------------------------------------------
# Lightweight entity for behavioral testing
# ---------------------------------------------------------------------------

class BehavioralEntity:
    """Lightweight entity for behavioral testing (no DB/trigger/UI deps)."""

    def __init__(
        self,
        name: str,
        entity_type: str,
        hp: int,
        armor_class: int = 12,
        speed: int = 30,
        dex: int = 10,
        position: tuple[int, int] = (0, 0),
    ):
        self.name = name
        self.entity_type = entity_type
        self.hp = hp
        self.max_hp = hp
        self.armor_class = armor_class
        self.speed = speed
        self.stats = {"Dexterity": dex, "max_hp": hp}
        self.conditions: list[str] = []
        self.position = position
        self.initiative = 0
        self.triggers: list = []
        self.inventory: list = []
        self.personality: EntityPersonality | None = None
        self.portraits: dict[str, str] = {}
        self.image_path: str | None = None

    @property
    def hp_percent(self) -> float:
        if self.max_hp <= 0:
            return 0.0
        return self.hp / self.max_hp


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class ScenarioConfig:
    """Describes a repeatable combat scenario."""

    name: str
    description: str = ""
    entities: list[dict] = field(default_factory=list)
    map_size: tuple[int, int] = (10, 10)
    max_rounds: int = 20

    @classmethod
    def from_yaml(cls, path: str) -> ScenarioConfig:
        """Load scenario from a YAML file."""
        import yaml  # optional dep — only needed for YAML scenarios
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            entities=data.get("entities", []),
            map_size=tuple(data.get("map_size", [10, 10])),
            max_rounds=data.get("max_rounds", 20),
        )


@dataclass
class HarnessConfig:
    """Controls how many runs and in what mode."""

    runs: int = 100
    seed_start: int = 1
    parallel_workers: int = 4
    use_real_ai: bool = False
    timeout_per_run: int = 60


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class HarnessResult:
    """Aggregated result of many behavioral runs."""

    scenario_name: str
    config: HarnessConfig
    stats_by_entity: dict[str, BehaviorStats]
    total_runs: int
    successful_runs: int
    failed_runs: int
    total_time_seconds: float

    @property
    def runs_per_second(self) -> float:
        if self.total_time_seconds <= 0:
            return 0.0
        return self.total_runs / self.total_time_seconds

    def get_alignment_stats(self, alignment: str) -> list[BehaviorStats]:
        """Get all entity stats matching an alignment string."""
        normalized = alignment.lower().replace(" ", "_")
        return [
            s for s in self.stats_by_entity.values()
            if s.alignment.lower().replace(" ", "_") == normalized
        ]


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

class BehavioralTestHarness:
    """Runs N combat sessions and aggregates behavioral statistics."""

    def __init__(
        self,
        scenario: ScenarioConfig,
        config: HarnessConfig | None = None,
        adapter_factory: Callable | None = None,
    ):
        self._scenario = scenario
        self._config = config or HarnessConfig()
        self._adapter_factory = adapter_factory

    def run(self) -> HarnessResult:
        """Execute all runs and return aggregated results."""
        start = time.time()

        if self._config.use_real_ai:
            results = self._run_sequential()
        else:
            results = self._run_parallel()

        elapsed = time.time() - start

        # Merge per-run stats into aggregated BehaviorStats
        all_stats: dict[str, list[EntityRunStats]] = {}
        successful = 0
        failed = 0
        for run_result in results:
            if run_result is None:
                failed += 1
                continue
            successful += 1
            for name, run_stats in run_result.items():
                all_stats.setdefault(name, []).append(run_stats)

        stats_by_entity = {}
        for name, runs in all_stats.items():
            if runs:
                stats_by_entity[name] = BehaviorStats(
                    entity_name=name,
                    alignment=runs[0].alignment,
                    runs=runs,
                )

        return HarnessResult(
            scenario_name=self._scenario.name,
            config=self._config,
            stats_by_entity=stats_by_entity,
            total_runs=self._config.runs,
            successful_runs=successful,
            failed_runs=failed,
            total_time_seconds=elapsed,
        )

    # ------------------------------------------------------------------
    # Run strategies
    # ------------------------------------------------------------------

    def _run_parallel(self) -> list[dict[str, EntityRunStats] | None]:
        results: list[dict[str, EntityRunStats] | None] = [None] * self._config.runs
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self._config.parallel_workers
        ) as executor:
            future_to_idx = {}
            for i in range(self._config.runs):
                seed = self._config.seed_start + i
                future = executor.submit(self._run_single, seed, i)
                future_to_idx[future] = i
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result(timeout=self._config.timeout_per_run)
                except Exception:
                    results[idx] = None
        return results

    def _run_sequential(self) -> list[dict[str, EntityRunStats] | None]:
        results = []
        for i in range(self._config.runs):
            seed = self._config.seed_start + i
            try:
                results.append(self._run_single(seed, i))
            except Exception:
                results.append(None)
        return results

    # ------------------------------------------------------------------
    # Single run
    # ------------------------------------------------------------------

    def _run_single(self, seed: int, run_id: int) -> dict[str, EntityRunStats]:
        rng = random.Random(seed)

        # Build Gamemaster + World
        gm = Gamemaster()
        gm.world = World(
            world_version=1,
            width=self._scenario.map_size[0],
            height=self._scenario.map_size[1],
            tile_type="square",
            description=self._scenario.description,
            map_data={},
            time_of_day="",
            weather_conditions="",
        )
        gm.world_tile_manager = gm.world.tile_manager

        # Create entities
        entities_by_name: dict[str, BehavioralEntity] = {}
        run_stats: dict[str, EntityRunStats] = {}

        for cfg in self._scenario.entities:
            entity = self._create_entity(cfg)
            pos = cfg.get("position", [0, 0])
            gm.world_tile_manager.place_entity(entity, pos[0], pos[1])
            gm.add_entity(entity)
            entities_by_name[entity.name] = entity

            alignment_str = cfg.get("alignment", "true_neutral")
            run_stats[entity.name] = EntityRunStats(
                entity_name=entity.name,
                alignment=alignment_str,
                run_id=run_id,
                seed=seed,
            )

        # Round number tracker for MockAI
        current_round = [1]

        def on_round_start(state):
            current_round[0] = state.round_number

        # Create adapters
        if self._adapter_factory:
            adapters = self._adapter_factory(entities_by_name, rng, run_stats)
        else:
            adapters = self._create_default_adapters(
                entities_by_name, rng, run_stats,
                round_number_fn=lambda: current_round[0],
            )

        # Run session
        session = GameSession(
            gm, adapters, seed=seed,
            max_rounds=self._scenario.max_rounds,
            on_round_start=on_round_start,
            on_action_result=lambda r: self._on_action(r, run_stats),
        )
        session.setup()
        result = session.run()

        # Finalize stats
        for name, stats in run_stats.items():
            entity = entities_by_name[name]
            stats.rounds_survived = result.rounds_played
            stats.final_hp_percent = entity.hp / entity.max_hp if entity.max_hp > 0 else 0.0
            stats.died = entity.hp <= 0

        return run_stats

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_entity(self, cfg: dict) -> BehavioralEntity:
        entity = BehavioralEntity(
            name=cfg["name"],
            entity_type=cfg.get("type", "enemy"),
            hp=cfg.get("hp", 10),
            armor_class=cfg.get("armor_class", 12),
            speed=cfg.get("speed", 30),
            dex=cfg.get("dex", 10),
            position=tuple(cfg.get("position", [0, 0])),
        )
        alignment_str = cfg.get("alignment", "true neutral")
        # Normalize underscores to spaces for Alignment.from_string
        alignment = Alignment.from_string(alignment_str.replace("_", " "))
        personality = EntityPersonality(alignment=alignment)
        if cfg.get("trait"):
            personality.trait = cfg["trait"]
        entity.personality = personality
        return entity

    def _create_default_adapters(
        self,
        entities_by_name: dict[str, Any],
        rng: random.Random,
        run_stats: dict[str, EntityRunStats],
        round_number_fn: Callable[[], int] | None = None,
    ) -> dict[str, InputAdapter]:
        mock = MockAIAdapter(
            entities_by_name=entities_by_name,
            rng=rng,
            stats_collector=run_stats,
            round_number_fn=round_number_fn,
        )
        return {name: mock for name in entities_by_name}

    def _on_action(self, result, run_stats: dict[str, EntityRunStats]) -> None:
        """Extract damage/kill stats from ActionResult."""
        if not result.success or result.action is None:
            return

        action = result.action
        actor_name = getattr(getattr(action, "actor", None), "name", None)
        if not actor_name:
            return

        if isinstance(action, AttackAction):
            target_name = getattr(action.target, "name", None)
            for log_entry in result.execution_log:
                match = re.search(r"for (\d+) damage", log_entry)
                if match:
                    dmg = int(match.group(1))
                    if actor_name in run_stats:
                        run_stats[actor_name].damage_dealt += dmg
                        run_stats[actor_name].record(0, BehaviorEvent.DEALT_DAMAGE, amount=dmg)
                    if target_name and target_name in run_stats:
                        run_stats[target_name].damage_taken += dmg
                        run_stats[target_name].record(0, BehaviorEvent.TOOK_DAMAGE, amount=dmg)

                    # Check for kill
                    if hasattr(action.target, "hp") and action.target.hp <= 0:
                        if actor_name in run_stats:
                            run_stats[actor_name].kills += 1
                            run_stats[actor_name].record(0, BehaviorEvent.KILLED_ENEMY)
                        if target_name and target_name in run_stats:
                            run_stats[target_name].record(0, BehaviorEvent.DIED)

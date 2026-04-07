"""Sandboxed scene simulation for DM rehearsal.

Wraps GameSession + HeuristicAIAdapter in a safe sandbox that
isolates the EventBus to prevent side effects on the editor state.

Usage::

    with SceneSimulator(entity_dicts) as sim:
        result = sim.run_to_completion()
        print(result.winner, result.rounds_played)
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SimulationConfig:
    """Configuration knobs for a simulation run."""

    seed: int = 42
    max_rounds: int = 20


@dataclass
class SimulationResult:
    """Outcome of a completed simulation."""

    rounds_played: int
    winner: str | None  # "player" | "enemy" | None
    action_log: list[str]
    final_entity_states: list[dict]


class SceneSimulator:
    """Sandboxed combat simulation.

    Accepts entity dicts (``GameEntity.to_dict()`` format) and replays
    them inside an isolated :class:`GameSession` with deterministic
    :class:`HeuristicAIAdapter` instances.

    The context-manager protocol snapshots the global
    :class:`EventBus` subscribers on entry and restores them on exit,
    guaranteeing no side effects leak into the editor.

    Parameters
    ----------
    entities:
        ``list[dict]`` — one dict per entity in ``GameEntity.to_dict()``
        format.
    config:
        Optional :class:`SimulationConfig`.  Defaults to seed=42,
        max_rounds=20.
    """

    def __init__(
        self,
        entities: list[dict],
        config: SimulationConfig | None = None,
    ) -> None:
        if not entities:
            raise ValueError("At least one entity is required")
        self._entity_dicts = entities
        self._config = config or SimulationConfig()
        self._session: Any = None
        self._action_log: list[str] = []
        self._saved_subscribers: dict | None = None
        self._setup_done = False

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def setup(self) -> None:
        """Snapshot EventBus, build a fresh GameSession."""
        from core.gameCreation.event_bus import EventBus

        # 1. Save current EventBus subscriber state (deep copy so we
        #    hold an independent snapshot of every list).
        inst = EventBus._get_instance()
        self._saved_subscribers = {
            k: list(v) for k, v in inst._subscribers.items()
        }

        # 2. Reset EventBus — clear all subscribers so that entity
        #    triggers registered below don't collide with the editor.
        EventBus.reset()

        # 3. Hydrate GameEntity objects from dicts.  from_dict() calls
        #    register_trigger() which subscribes to the (now clean) bus.
        from models.entities.game_entity import GameEntity

        entities = [GameEntity.from_dict(d) for d in self._entity_dicts]

        # Ensure every entity has a position (default to spread along
        # row 0 if none was serialised).
        for idx, entity in enumerate(entities):
            if entity.position is None:
                entity.position = (idx, 0)

        # 4. Build a fresh Gamemaster and populate it.
        from models.game_master import Gamemaster

        gm = Gamemaster()
        for entity in entities:
            gm.add_entity(entity)

        # 5. Build one HeuristicAIAdapter per entity.
        from core.engine.ai.heuristic_adapter import HeuristicAIAdapter

        rng = random.Random(self._config.seed)
        entities_by_name: dict[str, GameEntity] = {
            e.name: e for e in entities
        }
        adapters: dict[str, HeuristicAIAdapter] = {}
        for entity in entities:
            adapters[entity.name] = HeuristicAIAdapter(
                entities_by_name=entities_by_name,
                rng=random.Random(rng.randint(0, 2**31)),
            )

        # 6. Wire up logging callbacks.
        self._action_log.clear()

        def _on_round_start(state: Any) -> None:
            self._action_log.append(f"--- Round {state.round_number} ---")

        def _on_action_result(result: Any) -> None:
            action = result.action
            if action is None:
                return
            actor = getattr(action, "actor", None)
            actor_name = getattr(actor, "name", "?") if actor else "?"
            action_type = action.__class__.__name__
            success = "OK" if result.success else "FAIL"
            self._action_log.append(
                f"  {actor_name}: {action_type} [{success}]"
            )

        # 7. Build GameSession.
        from core.engine.game_session import GameSession

        self._session = GameSession(
            gamemaster=gm,
            adapters=adapters,
            seed=self._config.seed,
            max_rounds=self._config.max_rounds,
            on_round_start=_on_round_start,
            on_action_result=_on_action_result,
        )
        self._session.setup(entities)
        self._setup_done = True

    def cleanup(self) -> None:
        """Restore EventBus subscribers saved during :meth:`setup`."""
        if self._saved_subscribers is not None:
            from core.gameCreation.event_bus import EventBus

            inst = EventBus._get_instance()
            inst._subscribers = self._saved_subscribers
            self._saved_subscribers = None
        self._session = None
        self._setup_done = False

    def reset(self) -> None:
        """Tear down and re-build the simulation from scratch."""
        self.cleanup()
        self.setup()

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #

    def run_one_round(self) -> list[str]:
        """Run one combat round.  Returns the new log lines produced."""
        if not self._setup_done:
            self.setup()
        before = len(self._action_log)
        self._session.run_one_round()
        return self._action_log[before:]

    def run_to_completion(self) -> SimulationResult:
        """Run combat until a termination condition is reached."""
        if not self._setup_done:
            self.setup()

        session_result = self._session.run()

        # Build final entity states from the session's GameState snapshot.
        state = self._session.get_state()
        final: list[dict] = []
        for es in state.entities:
            final.append(
                {
                    "name": es.name,
                    "entity_type": es.entity_type,
                    "hp": es.hp,
                    "max_hp": es.max_hp,
                    "is_alive": es.is_alive,
                    "conditions": list(es.conditions),
                }
            )

        return SimulationResult(
            rounds_played=session_result.rounds_played,
            winner=session_result.winner,
            action_log=list(self._action_log),
            final_entity_states=final,
        )

    # ------------------------------------------------------------------ #
    # Inspection
    # ------------------------------------------------------------------ #

    def get_state(self) -> Any:
        """Return the current :class:`GameState` snapshot, or ``None``."""
        if self._session is not None:
            return self._session.get_state()
        return None

    @property
    def is_finished(self) -> bool:
        """``True`` when the underlying session has reached an end state."""
        if self._session is not None:
            return self._session.is_finished
        return False

    # ------------------------------------------------------------------ #
    # Context manager
    # ------------------------------------------------------------------ #

    def __enter__(self) -> SceneSimulator:
        self.setup()
        return self

    def __exit__(self, *exc: object) -> None:
        self.cleanup()

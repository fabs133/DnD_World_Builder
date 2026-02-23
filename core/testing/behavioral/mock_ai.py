"""Deterministic AI adapter using TacticalWeights + seeded RNG (no LLM)."""

from __future__ import annotations

import random
from typing import Any, Callable

from core.engine.input_adapter import InputAdapter
from core.engine.game_state import GameState
from core.engine.actions.attack_action import AttackAction
from core.engine.actions.end_turn_action import EndTurnAction
from core.engine.actions.move_action import MoveAction
from core.testing.behavioral.stats import BehaviorEvent, EntityRunStats
from models.ai.tactical_weights import TacticalWeights


# Faction helpers
_PLAYER_TYPES = {"player", "ally", "companion"}
_ENEMY_TYPES = {"enemy", "monster", "hostile"}


def _are_allies(type_a: str, type_b: str) -> bool:
    a, b = type_a.lower(), type_b.lower()
    if a in _PLAYER_TYPES and b in _PLAYER_TYPES:
        return True
    if a in _ENEMY_TYPES and b in _ENEMY_TYPES:
        return True
    return False


def _manhattan(pos_a: tuple[int, int], pos_b: tuple[int, int]) -> int:
    return abs(pos_a[0] - pos_b[0]) + abs(pos_a[1] - pos_b[1])


class MockAIAdapter(InputAdapter):
    """Deterministic AI driven by TacticalWeights + seeded RNG.

    No LLM calls. Uses the entity's personality weights to make
    probabilistic-but-reproducible decisions. Fast enough for
    thousands of CI runs.
    """

    def __init__(
        self,
        entities_by_name: dict[str, Any],
        rng: random.Random | None = None,
        stats_collector: dict[str, EntityRunStats] | None = None,
        round_number_fn: Callable[[], int] | None = None,
    ):
        self._entities = entities_by_name
        self._rng = rng or random.Random()
        self._stats = stats_collector or {}
        self._round_fn = round_number_fn or (lambda: 1)
        # Track last target per entity for coordination/entropy
        self._last_targets: dict[str, str] = {}

    # ------------------------------------------------------------------
    # InputAdapter interface
    # ------------------------------------------------------------------

    def choose_action(
        self,
        entity_name: str,
        game_state: GameState,
        available_actions: list[str],
    ):
        actor = self._entities.get(entity_name)
        if actor is None:
            return EndTurnAction(actor=type("Dummy", (), {"name": entity_name})())

        weights = self._get_weights(actor)
        hp_pct = self._hp_percent(actor)
        my_type = getattr(actor, "entity_type", "enemy").lower()

        # 1. FLEE CHECK
        if hp_pct < weights.flee_threshold:
            self._record(entity_name, BehaviorEvent.CONSIDERED_FLEEING)
            if self._rng.random() < weights.flee_threshold:
                self._record(entity_name, BehaviorEvent.FLED_COMBAT)
                return EndTurnAction(actor=actor)
            else:
                self._record(entity_name, BehaviorEvent.STAYED_DESPITE_DANGER)

        # 2. PROTECT CHECK — look for low-HP allies
        if "ATTACK" in available_actions:
            ally_in_danger = self._find_threatened_ally(actor, my_type)
            if ally_in_danger is not None:
                self._record(entity_name, BehaviorEvent.ALLY_THREATENED)
                if self._rng.random() < weights.ally_protection:
                    self._record(entity_name, BehaviorEvent.PROTECTED_ALLY)
                    # Attack nearest enemy to the threatened ally
                    protector_target = self._find_enemy_near(ally_in_danger, my_type)
                    if protector_target is not None:
                        self._record(entity_name, BehaviorEvent.ATTACKED)
                        self._last_targets[entity_name] = protector_target.name
                        return AttackAction(
                            actor=actor, target=protector_target,
                            damage_expr="1d6", rng=self._rng,
                        )
                else:
                    self._record(entity_name, BehaviorEvent.IGNORED_DYING_ALLY)

        # 3. MERCY CHECK — downed enemies
        if "ATTACK" in available_actions:
            downed = self._find_downed_enemies(my_type)
            if downed:
                self._record(entity_name, BehaviorEvent.COULD_EXECUTE_DOWNED)
                if self._rng.random() > weights.mercy:
                    # Low mercy = execute
                    self._record(entity_name, BehaviorEvent.EXECUTED_DOWNED)
                    # Already at 0 HP — record but don't attack (they're dead)
                else:
                    self._record(entity_name, BehaviorEvent.SPARED_DOWNED)

        # 4. STANDARD ATTACK
        if "ATTACK" in available_actions:
            target = self._pick_target(entity_name, actor, my_type, game_state)
            if target is not None:
                self._record(entity_name, BehaviorEvent.ATTACKED)
                self._last_targets[entity_name] = target.name
                return AttackAction(
                    actor=actor, target=target,
                    damage_expr="1d6", rng=self._rng,
                )

        # 5. FALLBACK
        return EndTurnAction(actor=actor)

    def choose_target(
        self,
        entity_name: str,
        game_state: GameState,
        valid_targets: list[str],
    ) -> str:
        if not valid_targets:
            return ""
        actor = self._entities.get(entity_name)
        if actor is None:
            return valid_targets[0]

        weights = self._get_weights(actor)
        my_type = getattr(actor, "entity_type", "enemy").lower()

        # Filter to alive enemies
        enemies = []
        for name in valid_targets:
            ent = self._entities.get(name)
            if ent and getattr(ent, "hp", 0) > 0:
                enemies.append(ent)
        if not enemies:
            return valid_targets[0]

        target = self._select_by_weights(entity_name, actor, weights, enemies)
        return target.name

    def choose_movement(
        self,
        entity_name: str,
        game_state: GameState,
        valid_positions: list[tuple[int, int]],
    ) -> tuple[int, int]:
        if not valid_positions:
            actor = self._entities.get(entity_name)
            return getattr(actor, "position", (0, 0)) if actor else (0, 0)

        actor = self._entities.get(entity_name)
        if actor is None:
            return valid_positions[0]

        weights = self._get_weights(actor)
        my_type = getattr(actor, "entity_type", "enemy").lower()
        my_pos = getattr(actor, "position", (0, 0))

        enemies = self._get_alive_enemies(my_type)
        allies = self._get_alive_allies(my_type, entity_name)

        # Aggressive: move toward nearest enemy
        if weights.aggression > 0.6 and enemies:
            nearest_enemy = min(enemies, key=lambda e: _manhattan(my_pos, getattr(e, "position", (0, 0))))
            enemy_pos = getattr(nearest_enemy, "position", (0, 0))
            return min(valid_positions, key=lambda p: _manhattan(p, enemy_pos))

        # Defensive: move away from enemies
        if weights.aggression < 0.4 and enemies:
            nearest_enemy = min(enemies, key=lambda e: _manhattan(my_pos, getattr(e, "position", (0, 0))))
            enemy_pos = getattr(nearest_enemy, "position", (0, 0))
            return max(valid_positions, key=lambda p: _manhattan(p, enemy_pos))

        # Protective: move toward weakest ally
        if weights.ally_protection > 0.6 and allies:
            weakest = min(allies, key=lambda e: getattr(e, "hp", 0))
            ally_pos = getattr(weakest, "position", (0, 0))
            return min(valid_positions, key=lambda p: _manhattan(p, ally_pos))

        return valid_positions[0]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record(self, entity_name: str, event: BehaviorEvent, **meta) -> None:
        if entity_name in self._stats:
            self._stats[entity_name].record(self._round_fn(), event, **meta)

    def _get_weights(self, actor: Any) -> TacticalWeights:
        personality = getattr(actor, "personality", None)
        if personality is not None:
            return personality.tactical_weights
        return TacticalWeights()  # neutral defaults

    def _hp_percent(self, actor: Any) -> float:
        hp = getattr(actor, "hp", 0)
        max_hp = getattr(actor, "max_hp", None) or getattr(actor, "stats", {}).get("max_hp", hp)
        if not max_hp or max_hp <= 0:
            return 1.0
        return hp / max_hp

    def _get_alive_enemies(self, my_type: str) -> list[Any]:
        result = []
        for ent in self._entities.values():
            etype = getattr(ent, "entity_type", "").lower()
            if not _are_allies(my_type, etype) and getattr(ent, "hp", 0) > 0:
                result.append(ent)
        return result

    def _get_alive_allies(self, my_type: str, exclude_name: str = "") -> list[Any]:
        result = []
        for ent in self._entities.values():
            if ent.name == exclude_name:
                continue
            etype = getattr(ent, "entity_type", "").lower()
            if _are_allies(my_type, etype) and getattr(ent, "hp", 0) > 0:
                result.append(ent)
        return result

    def _find_threatened_ally(self, actor: Any, my_type: str) -> Any | None:
        """Find an ally below 30% HP."""
        for ent in self._get_alive_allies(my_type, actor.name):
            if self._hp_percent(ent) < 0.3:
                return ent
        return None

    def _find_enemy_near(self, ally: Any, my_type: str) -> Any | None:
        """Find nearest enemy to a given ally."""
        ally_pos = getattr(ally, "position", (0, 0))
        enemies = self._get_alive_enemies(my_type)
        if not enemies:
            return None
        return min(enemies, key=lambda e: _manhattan(ally_pos, getattr(e, "position", (0, 0))))

    def _find_downed_enemies(self, my_type: str) -> list[Any]:
        """Find enemies at exactly 0 HP (downed but trackable)."""
        result = []
        for ent in self._entities.values():
            etype = getattr(ent, "entity_type", "").lower()
            if not _are_allies(my_type, etype) and getattr(ent, "hp", 0) <= 0:
                result.append(ent)
        return result

    def _pick_target(
        self, entity_name: str, actor: Any, my_type: str, game_state: GameState
    ) -> Any | None:
        weights = self._get_weights(actor)
        enemies = self._get_alive_enemies(my_type)
        if not enemies:
            return None

        target = self._select_by_weights(entity_name, actor, weights, enemies)

        # Coordination: chance to focus-fire if ally is attacking same target
        if weights.coordination > 0.6 and self._rng.random() < weights.coordination:
            ally_targets = set()
            for name, last in self._last_targets.items():
                other = self._entities.get(name)
                if other and _are_allies(my_type, getattr(other, "entity_type", "").lower()):
                    if name != entity_name and last:
                        ally_targets.add(last)
            # Pick an ally's target if it's alive
            for tname in ally_targets:
                tent = self._entities.get(tname)
                if tent and getattr(tent, "hp", 0) > 0 and tent in enemies:
                    self._record(entity_name, BehaviorEvent.FOCUS_FIRED)
                    return tent

        return target

    def _select_by_weights(
        self, entity_name: str, actor: Any, weights: TacticalWeights,
        enemies: list[Any],
    ) -> Any:
        """Select a target based on tactical weights."""
        my_pos = getattr(actor, "position", (0, 0))

        # Unpredictable: random target
        if weights.predictability < 0.3 and self._rng.random() < (1 - weights.predictability):
            self._record(entity_name, BehaviorEvent.TARGETED_RANDOM)
            return self._rng.choice(enemies)

        # Target weakest
        if weights.target_priority < 0.3:
            self._record(entity_name, BehaviorEvent.TARGETED_WEAKEST)
            return min(enemies, key=lambda e: getattr(e, "hp", 0))

        # Target strongest
        if weights.target_priority > 0.7:
            self._record(entity_name, BehaviorEvent.TARGETED_STRONGEST)
            return max(enemies, key=lambda e: getattr(e, "hp", 0))

        # Default: nearest
        self._record(entity_name, BehaviorEvent.TARGETED_NEAREST)
        return min(enemies, key=lambda e: _manhattan(my_pos, getattr(e, "position", (0, 0))))

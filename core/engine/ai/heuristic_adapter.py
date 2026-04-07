"""Deterministic AI adapter that uses heuristic rules instead of an LLM.

When Ollama is unavailable this adapter provides real tactical behaviour
driven by the entity's :class:`~models.ai.tactical_weights.TacticalWeights`.
All decisions are pure functions of ``(entity_state, game_state, rng)``
— no I/O, fully deterministic with a fixed seed.
"""

from __future__ import annotations

import random
import re
from typing import Any

from core.logger import app_logger
from core.engine.input_adapter import InputAdapter
from core.engine.game_state import GameState, EntitySnapshot
from core.engine.actions.attack_action import AttackAction
from core.engine.actions.move_action import MoveAction
from core.engine.actions.end_turn_action import EndTurnAction
from core.engine.ai.combat_utils import (
    are_allies, find_weakest_target, get_actor, get_personality,
    get_enemies,
)
from models.flow.action.action import Action
from models.ai.personality import EntityPersonality
from models.ai.alignment import Alignment


class HeuristicAIAdapter(InputAdapter):
    """Rule-based AI that reads TacticalWeights to decide actions.

    Decision logic (evaluated top-to-bottom):

    1. **Flee** — if ``hp_ratio < weights.flee_threshold`` and a move is
       available, move away from all enemies.
    2. **Attack** — if an enemy is adjacent (melee range) and ATTACK is
       available, attack the lowest-HP adjacent enemy.
    3. **Advance** — if enemies exist and MOVE is available, move toward
       the nearest enemy.
    4. **End turn** — fallback when nothing useful can be done.
    """

    def __init__(
        self,
        entities_by_name: dict[str, Any] | None = None,
        rng: random.Random | None = None,
        default_personality: EntityPersonality | None = None,
        tile_map: Any | None = None,
    ):
        self._entities_by_name = entities_by_name or {}
        self._rng = rng or random.Random()
        self._default_personality = default_personality or EntityPersonality(
            alignment=Alignment.TRUE_NEUTRAL,
        )
        self._tile_map = tile_map

    # --------------------------------------------------------------------- #
    # InputAdapter interface
    # --------------------------------------------------------------------- #

    def choose_action(
        self,
        entity_name: str,
        game_state: GameState,
        available_actions: list[str],
    ) -> Action:
        actor = self._get_actor(entity_name)
        personality = self._get_personality(actor)
        weights = personality.tactical_weights

        hp = getattr(actor, "hp", 0)
        max_hp = getattr(actor, "max_hp", 1) or 1
        hp_ratio = hp / max_hp

        actor_pos = getattr(actor, "position", (0, 0)) or (0, 0)
        speed = self._get_entity_speed(entity_name, game_state)

        enemies = self._get_enemies(entity_name, game_state)
        adjacent_enemies = self._adjacent_enemies(actor_pos, enemies)

        # 1) Flee
        if (
            hp_ratio < weights.flee_threshold
            and "MOVE" in available_actions
            and enemies
        ):
            flee_pos = self._position_away_from_enemies(actor_pos, enemies, game_state, speed)
            if flee_pos and flee_pos != actor_pos:
                app_logger.debug(
                    f"[Heuristic] {entity_name} flees to {flee_pos} "
                    f"(hp_ratio={hp_ratio:.2f} < threshold={weights.flee_threshold})"
                )
                return MoveAction(actor, flee_pos, world_tile_manager=self._tile_map)

        # 2) Attack adjacent enemy
        if adjacent_enemies and "ATTACK" in available_actions:
            target = self._pick_weakest(adjacent_enemies, game_state)
            if target is None:
                return EndTurnAction(actor)
            target_entity = self._get_actor(target.name)
            app_logger.debug(
                f"[Heuristic] {entity_name} attacks {target.name} (hp={target.hp})"
            )
            damage_expr, to_hit_bonus = self._get_attack_stats(actor)
            return AttackAction(
                actor,
                target_entity,
                damage_expr=damage_expr,
                to_hit_bonus=to_hit_bonus,
                rng=self._rng,
            )

        # 3) Move toward nearest enemy
        if enemies and "MOVE" in available_actions:
            advance_pos = self._position_toward_enemies(actor_pos, enemies, game_state, speed)
            if advance_pos and advance_pos != actor_pos:
                app_logger.debug(
                    f"[Heuristic] {entity_name} advances to {advance_pos}"
                )
                return MoveAction(actor, advance_pos, world_tile_manager=self._tile_map)

        # 4) Fallback
        app_logger.debug(f"[Heuristic] {entity_name} ends turn (no useful action)")
        return EndTurnAction(actor)

    def choose_target(
        self,
        entity_name: str,
        game_state: GameState,
        valid_targets: list[str],
    ) -> str:
        if not valid_targets:
            return ""
        return self._find_weakest_target(valid_targets, game_state)

    def choose_movement(
        self,
        entity_name: str,
        game_state: GameState,
        valid_positions: list[tuple[int, int]],
    ) -> tuple[int, int]:
        if not valid_positions:
            return (0, 0)

        actor = self._get_actor(entity_name)
        personality = self._get_personality(actor)
        weights = personality.tactical_weights

        enemies = self._get_enemies(entity_name, game_state)

        if weights.aggression > 0.6 and enemies:
            return self._closest_to_enemies(valid_positions, enemies)
        elif weights.aggression < 0.4 and enemies:
            return self._farthest_from_enemies(valid_positions, enemies)
        return valid_positions[0]

    # --------------------------------------------------------------------- #
    # Helpers — entity / personality lookup
    # --------------------------------------------------------------------- #

    def _get_actor(self, entity_name: str) -> Any:
        return get_actor(entity_name, self._entities_by_name)

    def _get_personality(self, actor: Any) -> EntityPersonality:
        return get_personality(actor, self._default_personality)

    def _get_entity_speed(self, entity_name: str, game_state: GameState) -> int:
        """Get entity speed from GameState snapshot (feet per turn)."""
        for snap in game_state.entities:
            if snap.name == entity_name:
                return snap.speed
        return 30  # D&D default

    # --------------------------------------------------------------------- #
    # Helpers — attack stats
    # --------------------------------------------------------------------- #

    @staticmethod
    def _get_attack_stats(actor: Any) -> tuple[str, int]:
        """Extract damage_expr and to_hit_bonus from the actor's data.

        Checks (in order):
        1. actor.attacks list (Enemy subclass format)
        2. actor.stats dict keys
        3. Fallback: derive to_hit from STR modifier, damage "1d6"
        """
        # 1. Enemy-style attacks list
        attacks = getattr(actor, "attacks", None)
        if attacks:
            atk = attacks[0]  # Use first/primary attack
            raw_damage = atk.get("damage", "1d6")
            # Strip damage type suffix (e.g. "1d6+2 piercing" -> "1d6+2")
            damage_expr = raw_damage.split()[0] if raw_damage else "1d6"
            to_hit = atk.get("to_hit", 0)
            return damage_expr, to_hit

        # 2. Stats dict
        stats = getattr(actor, "stats", {})
        damage_expr = stats.get("damage_expr", stats.get("damage", None))
        if damage_expr:
            damage_expr = damage_expr.split()[0]
            to_hit = stats.get("to_hit_bonus", stats.get("to_hit", 0))
            return damage_expr, to_hit

        # 3. Fallback: derive from STR modifier
        str_score = stats.get("Strength", 10)
        to_hit = (str_score - 10) // 2
        return "1d6", to_hit

    # --------------------------------------------------------------------- #
    # Helpers — enemy queries
    # --------------------------------------------------------------------- #

    def _get_enemies(
        self, actor_name: str, game_state: GameState
    ) -> list[EntitySnapshot]:
        """Return alive enemies of *actor_name*."""
        actor = self._get_actor(actor_name)
        actor_type = getattr(actor, "entity_type", "")
        return get_enemies(actor_name, actor_type, game_state)

    def _adjacent_enemies(
        self,
        actor_pos: tuple[int, int],
        enemies: list[EntitySnapshot],
    ) -> list[EntitySnapshot]:
        """Return enemies within 1 tile (Chebyshev) of *actor_pos*."""
        result: list[EntitySnapshot] = []
        for e in enemies:
            dx = abs(e.position[0] - actor_pos[0])
            dy = abs(e.position[1] - actor_pos[1])
            if max(dx, dy) <= 1:
                result.append(e)
        return result

    @staticmethod
    def _are_allies(type_a: str, type_b: str) -> bool:
        return are_allies(type_a, type_b)

    # --------------------------------------------------------------------- #
    # Helpers — target / position selection
    # --------------------------------------------------------------------- #

    @staticmethod
    def _pick_weakest(
        enemies: list[EntitySnapshot],
        game_state: GameState,
    ) -> EntitySnapshot | None:
        if not enemies:
            return None
        return min(enemies, key=lambda e: e.hp)

    def _find_weakest_target(
        self, valid_targets: list[str], game_state: GameState
    ) -> str:
        return find_weakest_target(valid_targets, game_state)

    def _position_toward_enemies(
        self,
        actor_pos: tuple[int, int],
        enemies: list[EntitySnapshot],
        game_state: GameState,
        speed: int = 30,
    ) -> tuple[int, int] | None:
        """Return the best tile to advance toward the nearest enemy.

        When a tile_map is available, uses A* pathfinding and walks along
        the path as far as the entity's speed budget allows.  Falls back
        to a simple 1-tile step otherwise.
        """
        if not enemies:
            return None

        nearest = min(
            enemies,
            key=lambda e: abs(e.position[0] - actor_pos[0])
            + abs(e.position[1] - actor_pos[1]),
        )
        target_pos = nearest.position

        # Pathfinder-aware movement
        if self._tile_map is not None:
            from core.engine.pathfinder import find_path

            path = find_path(actor_pos, target_pos, self._tile_map)
            if path and len(path) >= 2:
                best = actor_pos
                cost = 0
                for tile in path[1:]:
                    tile_cost = self._tile_map.get_movement_cost(*tile)
                    if cost + tile_cost > speed:
                        break
                    cost += tile_cost
                    best = tile
                if best != actor_pos:
                    return best

        # Fallback: 1-tile step
        candidates = self._adjacent_valid_tiles(actor_pos, game_state)
        if not candidates:
            return None

        return min(
            candidates,
            key=lambda p: abs(p[0] - target_pos[0]) + abs(p[1] - target_pos[1]),
        )

    def _position_away_from_enemies(
        self,
        actor_pos: tuple[int, int],
        enemies: list[EntitySnapshot],
        game_state: GameState,
        speed: int = 30,
    ) -> tuple[int, int] | None:
        """Return the best tile to flee from enemies.

        When a tile_map is available, uses Dijkstra flood-fill to find all
        reachable tiles within the speed budget and picks the one farthest
        from all enemies.  Falls back to a 1-tile step otherwise.
        """
        if not enemies:
            return None

        def min_enemy_dist(pos: tuple[int, int]) -> int:
            return min(
                abs(pos[0] - e.position[0]) + abs(pos[1] - e.position[1])
                for e in enemies
            )

        # Pathfinder-aware flee
        if self._tile_map is not None:
            from core.engine.pathfinder import reachable_tiles

            reachable = reachable_tiles(actor_pos, speed, self._tile_map)
            if reachable:
                best = max(reachable.keys(), key=min_enemy_dist)
                if best != actor_pos:
                    return best

        # Fallback: 1-tile step
        candidates = self._adjacent_valid_tiles(actor_pos, game_state)
        if not candidates:
            return None

        return max(candidates, key=min_enemy_dist)

    @staticmethod
    def _closest_to_enemies(
        positions: list[tuple[int, int]],
        enemies: list[EntitySnapshot],
    ) -> tuple[int, int]:
        if not positions:
            return (0, 0)
        if not enemies:
            return positions[0]
        enemy_positions = [e.position for e in enemies]
        return min(
            positions,
            key=lambda p: min(
                abs(p[0] - ep[0]) + abs(p[1] - ep[1]) for ep in enemy_positions
            ),
        )

    @staticmethod
    def _farthest_from_enemies(
        positions: list[tuple[int, int]],
        enemies: list[EntitySnapshot],
    ) -> tuple[int, int]:
        if not positions:
            return (0, 0)
        if not enemies:
            return positions[0]
        enemy_positions = [e.position for e in enemies]
        return max(
            positions,
            key=lambda p: min(
                abs(p[0] - ep[0]) + abs(p[1] - ep[1]) for ep in enemy_positions
            ),
        )

    def _adjacent_valid_tiles(
        self,
        pos: tuple[int, int],
        game_state: GameState,
    ) -> list[tuple[int, int]]:
        """Return tiles within 1 step that are in bounds and unoccupied."""
        if self._tile_map:
            candidates = self._tile_map.get_adjacent_tiles(pos[0], pos[1])
        else:
            # Fallback to 8-directional for square grids
            x, y = pos
            candidates = [
                (x - 1, y - 1), (x, y - 1), (x + 1, y - 1),
                (x - 1, y),                  (x + 1, y),
                (x - 1, y + 1), (x, y + 1), (x + 1, y + 1),
            ]
        occupied = self._occupied_positions(game_state)
        return [
            (cx, cy)
            for cx, cy in candidates
            if 0 <= cx < game_state.world_width
            and 0 <= cy < game_state.world_height
            and (cx, cy) not in occupied
        ]

    @staticmethod
    def _occupied_positions(game_state: GameState) -> frozenset[tuple[int, int]]:
        """Return positions occupied by alive entities."""
        return frozenset(
            e.position for e in game_state.entities
            if e.is_alive and e.position
        )

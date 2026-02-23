"""Deterministic AI adapter that uses heuristic rules instead of an LLM.

When Ollama is unavailable this adapter provides real tactical behaviour
driven by the entity's :class:`~models.ai.tactical_weights.TacticalWeights`.
All decisions are pure functions of ``(entity_state, game_state, rng)``
— no I/O, fully deterministic with a fixed seed.
"""

from __future__ import annotations

import random
from typing import Any

from core.logger import app_logger
from core.engine.input_adapter import InputAdapter
from core.engine.game_state import GameState, EntitySnapshot
from core.engine.actions.attack_action import AttackAction
from core.engine.actions.move_action import MoveAction
from core.engine.actions.end_turn_action import EndTurnAction
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
    ):
        self._entities_by_name = entities_by_name or {}
        self._rng = rng or random.Random()
        self._default_personality = default_personality or EntityPersonality(
            alignment=Alignment.TRUE_NEUTRAL,
        )

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

        enemies = self._get_enemies(entity_name, game_state)
        adjacent_enemies = self._adjacent_enemies(actor_pos, enemies)

        # 1) Flee
        if (
            hp_ratio < weights.flee_threshold
            and "MOVE" in available_actions
            and enemies
        ):
            flee_pos = self._position_away_from_enemies(actor_pos, enemies, game_state)
            if flee_pos and flee_pos != actor_pos:
                app_logger.debug(
                    f"[Heuristic] {entity_name} flees to {flee_pos} "
                    f"(hp_ratio={hp_ratio:.2f} < threshold={weights.flee_threshold})"
                )
                return MoveAction(actor, flee_pos, world_tile_manager=None)

        # 2) Attack adjacent enemy
        if adjacent_enemies and "ATTACK" in available_actions:
            target = self._pick_weakest(adjacent_enemies, game_state)
            target_entity = self._get_actor(target.name)
            app_logger.debug(
                f"[Heuristic] {entity_name} attacks {target.name} (hp={target.hp})"
            )
            return AttackAction(
                actor,
                target_entity,
                damage_expr="1d6",
                to_hit_bonus=0,
                rng=self._rng,
            )

        # 3) Move toward nearest enemy
        if enemies and "MOVE" in available_actions:
            advance_pos = self._position_toward_enemies(actor_pos, enemies, game_state)
            if advance_pos and advance_pos != actor_pos:
                app_logger.debug(
                    f"[Heuristic] {entity_name} advances to {advance_pos}"
                )
                return MoveAction(actor, advance_pos, world_tile_manager=None)

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
        if entity_name in self._entities_by_name:
            return self._entities_by_name[entity_name]

        class _Stub:
            name = entity_name
            entity_type = "creature"
            hp = 10
            max_hp = 10
            position = (0, 0)
            personality = None

        return _Stub()

    def _get_personality(self, actor: Any) -> EntityPersonality:
        personality = getattr(actor, "personality", None)
        if personality is not None:
            return personality
        return self._default_personality

    # --------------------------------------------------------------------- #
    # Helpers — enemy queries
    # --------------------------------------------------------------------- #

    def _get_enemies(
        self, actor_name: str, game_state: GameState
    ) -> list[EntitySnapshot]:
        """Return alive enemies of *actor_name*."""
        actor = self._get_actor(actor_name)
        actor_type = getattr(actor, "entity_type", "").lower()

        enemies: list[EntitySnapshot] = []
        for snap in game_state.entities:
            if snap.name == actor_name or not snap.is_alive:
                continue
            if not self._are_allies(actor_type, snap.entity_type.lower()):
                enemies.append(snap)
        return enemies

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
        player_types = {"player", "ally", "companion"}
        enemy_types = {"enemy", "monster", "hostile"}
        a_player = type_a in player_types
        b_player = type_b in player_types
        a_enemy = type_a in enemy_types
        b_enemy = type_b in enemy_types
        return (a_player and b_player) or (a_enemy and b_enemy)

    # --------------------------------------------------------------------- #
    # Helpers — target / position selection
    # --------------------------------------------------------------------- #

    @staticmethod
    def _pick_weakest(
        enemies: list[EntitySnapshot],
        game_state: GameState,
    ) -> EntitySnapshot:
        return min(enemies, key=lambda e: e.hp)

    def _find_weakest_target(
        self, valid_targets: list[str], game_state: GameState
    ) -> str:
        weakest = valid_targets[0]
        lowest_hp = float("inf")
        for snap in game_state.entities:
            if snap.name in valid_targets and snap.hp < lowest_hp:
                lowest_hp = snap.hp
                weakest = snap.name
        return weakest

    def _position_toward_enemies(
        self,
        actor_pos: tuple[int, int],
        enemies: list[EntitySnapshot],
        game_state: GameState,
    ) -> tuple[int, int] | None:
        """Return the adjacent tile that gets closest to the nearest enemy."""
        if not enemies:
            return None

        nearest = min(
            enemies,
            key=lambda e: abs(e.position[0] - actor_pos[0])
            + abs(e.position[1] - actor_pos[1]),
        )
        target_pos = nearest.position

        # Consider all tiles within 1 step (simple — no pathfinder yet)
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
    ) -> tuple[int, int] | None:
        """Return the adjacent tile that maximises distance from all enemies."""
        if not enemies:
            return None

        candidates = self._adjacent_valid_tiles(actor_pos, game_state)
        if not candidates:
            return None

        def min_enemy_dist(pos: tuple[int, int]) -> int:
            return min(
                abs(pos[0] - e.position[0]) + abs(pos[1] - e.position[1])
                for e in enemies
            )

        return max(candidates, key=min_enemy_dist)

    @staticmethod
    def _closest_to_enemies(
        positions: list[tuple[int, int]],
        enemies: list[EntitySnapshot],
    ) -> tuple[int, int]:
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
        """Return tiles within 1 step that are inside the grid bounds."""
        x, y = pos
        candidates = [
            (x - 1, y - 1), (x, y - 1), (x + 1, y - 1),
            (x - 1, y),                  (x + 1, y),
            (x - 1, y + 1), (x, y + 1), (x + 1, y + 1),
        ]
        return [
            (cx, cy)
            for cx, cy in candidates
            if 0 <= cx < game_state.world_width and 0 <= cy < game_state.world_height
        ]

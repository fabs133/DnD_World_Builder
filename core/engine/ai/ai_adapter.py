"""InputAdapter implementation backed by Ollama LLM with alignment-based personality."""

from __future__ import annotations

import random
from typing import Any

import requests

from core.logger import app_logger
from core.engine.input_adapter import InputAdapter
from core.engine.game_state import GameState
from core.engine.ai.ollama_client import OllamaClient
from core.engine.ai.action_parser import ActionParser, ParseError
from core.engine.ai.combat_utils import (
    are_allies, find_weakest_target, get_actor, get_personality,
)
from core.engine.actions.end_turn_action import EndTurnAction
from models.flow.action.action import Action
from models.ai.personality import EntityPersonality
from models.ai.alignment import Alignment
from models.ai.prompt_builder import (
    TacticalPromptBuilder,
    CombatantInfo,
    ActionOption,
    CombatMemory,
)

# Connection errors that indicate Ollama is unreachable (not a parse/logic bug).
_CONNECTION_ERRORS = (
    requests.ConnectionError,
    requests.Timeout,
    ConnectionError,
    OSError,
)


class AIAdapter(InputAdapter):
    """LLM-powered player adapter using alignment-based personality.

    Uses the rich EntityPersonality system from models/ai/ for decision-making.
    The alignment grid (Lawful Good → Chaotic Evil) drives tactical behavior.

    Retry loop:
    1. Build situation prompt with personality, combat memory, grudges
    2. Send to Ollama
    3. Parse response into Action
    4. If parse fails, retry with error feedback (up to max_retries)
    5. If all retries fail, fall back to EndTurnAction
    """

    def __init__(
        self,
        ollama_client: OllamaClient | None = None,
        default_personality: EntityPersonality | None = None,
        max_retries: int = 3,
        rng: random.Random | None = None,
        entities_by_name: dict[str, Any] | None = None,
    ):
        self._client = ollama_client or OllamaClient()
        self._prompt_builder = TacticalPromptBuilder()
        self._default_personality = default_personality or EntityPersonality(
            alignment=Alignment.TRUE_NEUTRAL
        )
        self._max_retries = max_retries
        self._rng = rng or random.Random()
        self._parser = ActionParser(rng=self._rng)
        self._entities_by_name = entities_by_name or {}

        # Combat memory per entity (persists across turns)
        self._combat_memories: dict[str, CombatMemory] = {}

        # Lazily created heuristic fallback (activated on first connection failure)
        self._fallback: "HeuristicAIAdapter | None" = None
        self._using_fallback = False

    def choose_action(
        self,
        entity_name: str,
        game_state: GameState,
        available_actions: list[str],
    ) -> Action:
        """Query LLM for action choice with retry loop.

        If the Ollama server is unreachable the adapter transparently
        switches to :class:`HeuristicAIAdapter` for the rest of the
        session and logs a single WARNING.
        """
        # Fast path: already switched to heuristic mode.
        if self._using_fallback:
            return self._get_fallback().choose_action(
                entity_name, game_state, available_actions,
            )

        actor = self._get_actor(entity_name)
        personality = self._get_personality(actor)
        memory = self._get_or_create_memory(entity_name)

        # Build combat info
        allies, enemies = self._categorize_combatants(entity_name, game_state)
        action_options = self._build_action_options(available_actions)

        # Get actor position and HP
        actor_hp = (getattr(actor, "hp", 10), getattr(actor, "max_hp", 10))
        actor_pos = getattr(actor, "position", (0, 0)) or (0, 0)

        previous_error = None

        for attempt in range(self._max_retries):
            prompt = self._prompt_builder.build_action_prompt(
                actor_name=entity_name,
                actor_type=getattr(actor, "entity_type", "creature"),
                actor_hp=actor_hp,
                actor_position=actor_pos,
                personality=personality,
                allies=allies,
                enemies=enemies,
                available_actions=action_options,
                memory=memory,
                additional_context=self._format_error_context(previous_error),
            )

            system_prompt = self._build_system_prompt(personality)

            try:
                response = self._client.generate(prompt, system=system_prompt)
                app_logger.debug(
                    f"[AI] {entity_name} attempt {attempt + 1}: {response.strip()[:100]}..."
                )
                action = self._parser.parse(
                    response, actor, game_state, self._entities_by_name,
                )
                return action
            except _CONNECTION_ERRORS as e:
                # Ollama is unreachable — switch to heuristic permanently.
                app_logger.warning(
                    f"[AI] Ollama unreachable ({e.__class__.__name__}): "
                    f"switching to HeuristicAIAdapter for all future calls"
                )
                self._using_fallback = True
                return self._get_fallback().choose_action(
                    entity_name, game_state, available_actions,
                )
            except ParseError as e:
                previous_error = str(e)
                app_logger.warning(
                    f"[AI] {entity_name} parse error (attempt {attempt + 1}): {e}"
                )
            except Exception as e:
                previous_error = str(e)
                app_logger.warning(
                    f"[AI] {entity_name} error (attempt {attempt + 1}): {e}"
                )

        app_logger.warning(
            f"[AI] {entity_name} failed all {self._max_retries} attempts, "
            f"falling back to first available action"
        )
        # Pick the first available action rather than wasting the turn
        if available_actions:
            from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
            return self._get_fallback().choose_action(
                entity_name, game_state, available_actions,
            )
        return EndTurnAction(actor)

    def choose_target(
        self,
        entity_name: str,
        game_state: GameState,
        valid_targets: list[str],
    ) -> str:
        """Choose a target based on personality."""
        if not valid_targets:
            return ""
        
        actor = self._get_actor(entity_name)
        personality = self._get_personality(actor)
        memory = self._get_or_create_memory(entity_name)
        
        # Check for grudge target
        grudge = memory.get_grudge_target()
        if grudge and grudge in valid_targets:
            app_logger.debug(f"[AI] {entity_name} targeting grudge: {grudge}")
            return grudge
        
        weights = personality.tactical_weights
        
        # Target priority: high = biggest threats, low = weakest targets
        if weights.target_priority < 0.4:
            # Target weakest (lowest HP)
            return self._find_weakest_target(valid_targets, game_state)
        else:
            # Target threats (default to first)
            return valid_targets[0]

    def choose_movement(
        self,
        entity_name: str,
        game_state: GameState,
        valid_positions: list[tuple[int, int]],
    ) -> tuple[int, int]:
        """Choose movement based on personality."""
        if not valid_positions:
            return (0, 0)
        
        actor = self._get_actor(entity_name)
        personality = self._get_personality(actor)
        weights = personality.tactical_weights
        
        # Simple heuristic based on aggression
        if weights.aggression > 0.6:
            # Move toward enemies
            return self._position_toward_enemies(
                entity_name, valid_positions, game_state
            )
        elif weights.aggression < 0.4:
            # Move away from enemies
            return self._position_away_from_enemies(
                entity_name, valid_positions, game_state
            )
        else:
            # Stay put or minimal movement
            return valid_positions[0]

    def record_damage(
        self,
        victim_name: str,
        attacker_name: str,
        amount: int,
        witnessed_by: list[str] | None = None,
    ) -> None:
        """Record damage for combat memory (grudges, etc.)."""
        # Victim remembers who hurt them
        victim_memory = self._get_or_create_memory(victim_name)
        victim_memory.record_damage_taken(attacker_name, amount)
        
        # Witnesses remember
        for witness in (witnessed_by or []):
            if witness != victim_name and witness != attacker_name:
                witness_memory = self._get_or_create_memory(witness)
                witness_memory.record_ally_damage(attacker_name, victim_name, amount)

    def record_kill(self, killer_name: str, victim_name: str) -> None:
        """Record a kill for combat memory."""
        killer_memory = self._get_or_create_memory(killer_name)
        killer_memory.record_kill(victim_name)
        
        # All allies of victim see them fall
        # (Would need faction info to implement fully)

    def reset_combat_memory(self, entity_name: str | None = None) -> None:
        """Clear combat memory for one or all entities."""
        if entity_name:
            self._combat_memories.pop(entity_name, None)
        else:
            self._combat_memories.clear()

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _get_actor(self, entity_name: str) -> Any:
        """Get the entity reference."""
        return get_actor(entity_name, self._entities_by_name)

    def _get_personality(self, actor: Any) -> EntityPersonality:
        """Get personality from actor or use default."""
        return get_personality(actor, self._default_personality)

    def _get_or_create_memory(self, entity_name: str) -> CombatMemory:
        """Get or create combat memory for entity."""
        if entity_name not in self._combat_memories:
            self._combat_memories[entity_name] = CombatMemory()
        return self._combat_memories[entity_name]

    def _categorize_combatants(
        self, actor_name: str, game_state: GameState
    ) -> tuple[list[CombatantInfo], list[CombatantInfo]]:
        """Split entities into allies and enemies relative to actor."""
        allies = []
        enemies = []

        actor = self._get_actor(actor_name)
        actor_type = getattr(actor, "entity_type", "")

        for entity_snap in game_state.entities:
            if entity_snap.name == actor_name:
                continue
            if not entity_snap.is_alive:
                continue

            etype = entity_snap.entity_type.lower()

            info = CombatantInfo(
                name=entity_snap.name,
                entity_type=etype,
                hp_current=entity_snap.hp,
                hp_max=entity_snap.max_hp,
                position=entity_snap.position,
                conditions=list(entity_snap.conditions),
            )

            # Simple faction logic
            if self._are_allies(actor_type, etype):
                info.is_ally = True
                allies.append(info)
            else:
                enemies.append(info)

        return allies, enemies

    def _are_allies(self, type_a: str, type_b: str) -> bool:
        """Check if two entity types are allied."""
        return are_allies(type_a, type_b)

    def _build_action_options(self, action_names: list[str]) -> list[ActionOption]:
        """Convert action name strings to ActionOption objects."""
        options = []
        for name in action_names:
            # Basic description based on action name
            desc = self._describe_action(name)
            options.append(ActionOption(
                name=name,
                description=desc,
                requires_target="attack" in name.lower() or "target" in name.lower(),
            ))
        return options

    def _describe_action(self, action_name: str) -> str:
        """Generate a basic description for an action."""
        name_lower = action_name.lower()
        if "attack" in name_lower:
            return "Make a melee or ranged attack"
        elif "move" in name_lower:
            return "Move to a new position"
        elif "dash" in name_lower:
            return "Double your movement speed this turn"
        elif "dodge" in name_lower:
            return "Focus on defense, attacks against you have disadvantage"
        elif "disengage" in name_lower:
            return "Withdraw without provoking opportunity attacks"
        elif "hide" in name_lower:
            return "Attempt to hide from enemies"
        elif "heal" in name_lower:
            return "Restore hit points"
        elif "cast" in name_lower or "spell" in name_lower:
            return "Cast a spell"
        elif "end" in name_lower or "pass" in name_lower:
            return "End your turn without acting"
        else:
            return f"Perform {action_name}"

    def _build_system_prompt(self, personality: EntityPersonality) -> str:
        """Build system prompt from personality."""
        lines = [
            "You are an AI controlling a character in D&D 5e combat.",
            "Make tactical decisions consistent with your alignment and personality.",
            "Respond with ONLY valid JSON. No explanation outside the JSON.",
            "",
            personality.format_for_prompt(),
        ]
        return "\n".join(lines)

    def _format_error_context(self, error: str | None) -> str:
        """Format previous error for retry context."""
        if not error:
            return ""
        return f"PREVIOUS ATTEMPT FAILED: {error}\nPlease fix the issue."

    def _find_weakest_target(
        self, valid_targets: list[str], game_state: GameState
    ) -> str:
        """Find the target with lowest HP."""
        return find_weakest_target(valid_targets, game_state)

    def _position_toward_enemies(
        self,
        actor_name: str,
        valid_positions: list[tuple[int, int]],
        game_state: GameState,
    ) -> tuple[int, int]:
        """Find position closest to nearest enemy."""
        enemy_positions = [
            e.position
            for e in game_state.entities
            if e.entity_type.lower() in {"enemy", "monster", "hostile"} and e.is_alive
        ]

        if not enemy_positions or not valid_positions:
            return valid_positions[0] if valid_positions else (0, 0)

        # Find nearest enemy
        actor = self._get_actor(actor_name)
        actor_pos = getattr(actor, "position", (0, 0)) or (0, 0)

        nearest_enemy_pos = min(
            enemy_positions,
            key=lambda p: abs(p[0] - actor_pos[0]) + abs(p[1] - actor_pos[1])
        )

        # Find valid position closest to that enemy
        return min(
            valid_positions,
            key=lambda p: abs(p[0] - nearest_enemy_pos[0]) + abs(p[1] - nearest_enemy_pos[1])
        )

    def _position_away_from_enemies(
        self,
        actor_name: str,
        valid_positions: list[tuple[int, int]],
        game_state: GameState,
    ) -> tuple[int, int]:
        """Find position farthest from nearest enemy."""
        enemy_positions = [
            e.position
            for e in game_state.entities
            if e.entity_type.lower() in {"enemy", "monster", "hostile"} and e.is_alive
        ]

        if not enemy_positions or not valid_positions:
            return valid_positions[0] if valid_positions else (0, 0)

        # Find position that maximizes minimum distance to any enemy
        def min_enemy_distance(pos):
            return min(
                abs(pos[0] - ep[0]) + abs(pos[1] - ep[1])
                for ep in enemy_positions
            )

        return max(valid_positions, key=min_enemy_distance)

    def _get_fallback(self) -> "HeuristicAIAdapter":
        """Return (and lazily create) the heuristic fallback adapter."""
        if self._fallback is None:
            from core.engine.ai.heuristic_adapter import HeuristicAIAdapter

            self._fallback = HeuristicAIAdapter(
                entities_by_name=self._entities_by_name,
                rng=self._rng,
                default_personality=self._default_personality,
            )
        return self._fallback

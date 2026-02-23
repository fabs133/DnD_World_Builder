# models/ai/prompt_builder.py
"""
Tactical Prompt Builder.

Generates prompts for AI-controlled entities based on their personality,
current game state, and available actions.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

from .personality import EntityPersonality


# =============================================================================
# PROTOCOLS (for type hints without hard dependencies)
# =============================================================================

class EntityLike(Protocol):
    """Protocol for entity-like objects."""
    name: str
    entity_type: str
    
    @property
    def stats(self) -> dict: ...


class ActionOptionLike(Protocol):
    """Protocol for action option objects."""
    name: str
    description: str


# =============================================================================
# COMBAT MEMORY
# =============================================================================

@dataclass
class CombatMemory:
    """
    Tracks events within a combat that influence AI decisions.
    
    This creates "grudge" behavior — the goblin remembers who killed their
    friend and prioritizes that target.
    """
    
    # Who hurt me? (entity_name -> total damage taken)
    damage_taken_from: dict[str, int] = field(default_factory=dict)
    
    # Who did I see hurt my allies? (entity_name -> total damage witnessed)
    witnessed_ally_damage: dict[str, int] = field(default_factory=dict)
    
    # Who healed me? (entity_name -> total healing received)
    healed_by: dict[str, int] = field(default_factory=dict)
    
    # Allies I've seen fall (entity names)
    fallen_allies: list[str] = field(default_factory=list)
    
    # Enemies I've defeated (entity names)
    kills: list[str] = field(default_factory=list)
    
    # Recent events for context (last N events)
    recent_events: list[str] = field(default_factory=list)
    
    MAX_RECENT_EVENTS: int = 5
    
    def record_damage_taken(self, attacker_name: str, amount: int) -> None:
        """Record damage taken from an attacker."""
        current = self.damage_taken_from.get(attacker_name, 0)
        self.damage_taken_from[attacker_name] = current + amount
        self._add_event(f"Took {amount} damage from {attacker_name}")
    
    def record_ally_damage(self, attacker_name: str, ally_name: str, amount: int) -> None:
        """Record damage witnessed to an ally."""
        current = self.witnessed_ally_damage.get(attacker_name, 0)
        self.witnessed_ally_damage[attacker_name] = current + amount
        self._add_event(f"Saw {attacker_name} deal {amount} damage to {ally_name}")
    
    def record_healing(self, healer_name: str, amount: int) -> None:
        """Record healing received."""
        current = self.healed_by.get(healer_name, 0)
        self.healed_by[healer_name] = current + amount
        self._add_event(f"Healed for {amount} by {healer_name}")
    
    def record_ally_fallen(self, ally_name: str) -> None:
        """Record an ally falling in combat."""
        if ally_name not in self.fallen_allies:
            self.fallen_allies.append(ally_name)
        self._add_event(f"Ally {ally_name} has fallen!")
    
    def record_kill(self, enemy_name: str) -> None:
        """Record defeating an enemy."""
        if enemy_name not in self.kills:
            self.kills.append(enemy_name)
        self._add_event(f"Defeated {enemy_name}")
    
    def _add_event(self, event: str) -> None:
        """Add an event to recent history."""
        self.recent_events.append(event)
        if len(self.recent_events) > self.MAX_RECENT_EVENTS:
            self.recent_events.pop(0)
    
    def get_grudge_target(self) -> str | None:
        """
        Get the entity that has hurt me or my allies the most.
        
        Returns None if no significant grudge exists.
        """
        # Combine direct damage and witnessed damage (weighted)
        scores: dict[str, float] = {}
        
        for name, damage in self.damage_taken_from.items():
            scores[name] = scores.get(name, 0) + damage * 1.0  # Direct damage
        
        for name, damage in self.witnessed_ally_damage.items():
            scores[name] = scores.get(name, 0) + damage * 0.5  # Witnessed damage
        
        if not scores:
            return None
        
        top_target = max(scores.items(), key=lambda x: x[1])
        
        # Only return if significant damage
        if top_target[1] >= 5:
            return top_target[0]
        return None
    
    def format_for_prompt(self) -> str:
        """Format combat memory for prompt inclusion."""
        lines = []
        
        grudge = self.get_grudge_target()
        if grudge:
            damage = self.damage_taken_from.get(grudge, 0)
            ally_damage = self.witnessed_ally_damage.get(grudge, 0)
            lines.append(f"GRUDGE TARGET: {grudge} (dealt {damage} damage to you, {ally_damage} to allies)")
        
        if self.fallen_allies:
            lines.append(f"FALLEN ALLIES: {', '.join(self.fallen_allies)}")
        
        if self.kills:
            lines.append(f"YOUR KILLS: {', '.join(self.kills)}")
        
        if self.recent_events:
            lines.append("RECENT EVENTS:")
            for event in self.recent_events[-3:]:  # Last 3
                lines.append(f"  • {event}")
        
        return "\n".join(lines) if lines else ""
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "damage_taken_from": self.damage_taken_from,
            "witnessed_ally_damage": self.witnessed_ally_damage,
            "healed_by": self.healed_by,
            "fallen_allies": self.fallen_allies,
            "kills": self.kills,
            "recent_events": self.recent_events,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CombatMemory:
        """Deserialize from dictionary."""
        return cls(
            damage_taken_from=data.get("damage_taken_from", {}),
            witnessed_ally_damage=data.get("witnessed_ally_damage", {}),
            healed_by=data.get("healed_by", {}),
            fallen_allies=data.get("fallen_allies", []),
            kills=data.get("kills", []),
            recent_events=data.get("recent_events", []),
        )


# =============================================================================
# TACTICAL PROMPT BUILDER
# =============================================================================

@dataclass
class CombatantInfo:
    """Information about a combatant for prompt building."""
    name: str
    entity_type: str  # "player", "enemy", "npc", "ally"
    hp_current: int
    hp_max: int
    position: tuple[int, int]
    conditions: list[str] = field(default_factory=list)
    is_ally: bool = False
    
    @property
    def hp_percent(self) -> float:
        """HP as a percentage."""
        if self.hp_max <= 0:
            return 0.0
        return self.hp_current / self.hp_max
    
    @property
    def hp_status(self) -> str:
        """Human-readable HP status."""
        pct = self.hp_percent
        if pct >= 0.9:
            return "healthy"
        elif pct >= 0.6:
            return "lightly wounded"
        elif pct >= 0.3:
            return "wounded"
        elif pct > 0:
            return "badly wounded"
        else:
            return "down"
    
    def format_for_prompt(self) -> str:
        """Format for prompt inclusion."""
        conditions_str = f" [{', '.join(self.conditions)}]" if self.conditions else ""
        return f"{self.name}: {self.hp_current}/{self.hp_max} HP ({self.hp_status}){conditions_str} at {self.position}"


@dataclass
class ActionOption:
    """An action available to the entity."""
    name: str
    description: str
    requires_target: bool = False
    valid_targets: list[str] = field(default_factory=list)
    
    def format_for_prompt(self, index: int) -> str:
        """Format for prompt inclusion."""
        target_str = ""
        if self.requires_target and self.valid_targets:
            target_str = f" [targets: {', '.join(self.valid_targets)}]"
        return f"{index}. {self.name}: {self.description}{target_str}"


class TacticalPromptBuilder:
    """
    Builds prompts for AI tactical decision-making.
    
    Assembles personality, game state, available actions, and combat memory
    into a prompt that guides the LLM to make in-character decisions.
    """
    
    # JSON schema for action response
    ACTION_SCHEMA = {
        "type": "object",
        "properties": {
            "action": {"type": "string"},
            "target": {"type": "string"},
            "reasoning": {"type": "string"},
        },
        "required": ["action", "reasoning"],
    }
    
    def __init__(
        self,
        include_voice_lines: bool = True,
        max_actions_shown: int = 6,
        include_memory: bool = True,
    ):
        """
        Initialize the prompt builder.
        
        Args:
            include_voice_lines: Whether to include example voice lines
            max_actions_shown: Maximum number of actions to show in prompt
            include_memory: Whether to include combat memory
        """
        self.include_voice_lines = include_voice_lines
        self.max_actions_shown = max_actions_shown
        self.include_memory = include_memory
    
    def build_action_prompt(
        self,
        actor_name: str,
        actor_type: str,
        actor_hp: tuple[int, int],  # (current, max)
        actor_position: tuple[int, int],
        personality: EntityPersonality,
        allies: list[CombatantInfo],
        enemies: list[CombatantInfo],
        available_actions: list[ActionOption],
        memory: CombatMemory | None = None,
        additional_context: str = "",
    ) -> str:
        """
        Build a complete action selection prompt.
        
        Returns a prompt string that asks the AI to choose an action
        and return it as JSON.
        """
        sections = []
        
        # Header
        sections.append(self._build_header(actor_name, actor_type, personality))
        
        # Personality section
        sections.append(personality.format_for_prompt())
        
        # Voice lines (optional flavor)
        if self.include_voice_lines and personality.voice_lines:
            line = random.choice(personality.voice_lines)
            sections.append(f'EXAMPLE VOICE LINE: "{line}"')
        
        # Memory (if enabled and present)
        if self.include_memory and memory:
            memory_str = memory.format_for_prompt()
            if memory_str:
                sections.append("")
                sections.append("=== COMBAT MEMORY ===")
                sections.append(memory_str)
        
        # Current state
        sections.append("")
        sections.append("=== CURRENT SITUATION ===")
        sections.append(self._build_state_section(
            actor_name, actor_hp, actor_position, allies, enemies
        ))
        
        # Additional context (terrain, triggers, etc.)
        if additional_context:
            sections.append("")
            sections.append("ADDITIONAL CONTEXT:")
            sections.append(additional_context)
        
        # Available actions
        sections.append("")
        sections.append("=== AVAILABLE ACTIONS ===")
        actions_str = self._build_actions_section(available_actions)
        sections.append(actions_str)
        
        # Response instructions
        sections.append("")
        sections.append(self._build_response_instructions(personality))
        
        return "\n".join(sections)
    
    def _build_header(
        self,
        actor_name: str,
        actor_type: str,
        personality: EntityPersonality,
    ) -> str:
        """Build the prompt header."""
        return (
            f"You are {actor_name}, a {actor_type}.\n"
            f"Alignment: {personality.alignment.name} — \"{personality.archetype}\""
        )
    
    def _build_state_section(
        self,
        actor_name: str,
        actor_hp: tuple[int, int],
        actor_position: tuple[int, int],
        allies: list[CombatantInfo],
        enemies: list[CombatantInfo],
    ) -> str:
        """Build the current state section."""
        lines = []
        
        # Self status
        hp_current, hp_max = actor_hp
        hp_pct = hp_current / hp_max if hp_max > 0 else 0
        if hp_pct >= 0.9:
            status = "healthy"
        elif hp_pct >= 0.6:
            status = "lightly wounded"
        elif hp_pct >= 0.3:
            status = "wounded"
        elif hp_pct > 0:
            status = "badly wounded"
        else:
            status = "dying"
        
        lines.append(f"YOUR STATUS: {hp_current}/{hp_max} HP ({status}) at {actor_position}")
        
        # Allies
        if allies:
            lines.append("")
            lines.append("ALLIES:")
            for ally in allies:
                lines.append(f"  • {ally.format_for_prompt()}")
        else:
            lines.append("\nALLIES: None")
        
        # Enemies
        if enemies:
            lines.append("")
            lines.append("ENEMIES:")
            for enemy in enemies:
                lines.append(f"  • {enemy.format_for_prompt()}")
        else:
            lines.append("\nENEMIES: None")
        
        return "\n".join(lines)
    
    def _build_actions_section(self, actions: list[ActionOption]) -> str:
        """Build the available actions section."""
        if not actions:
            return "No actions available. You must PASS."
        
        lines = []
        for i, action in enumerate(actions[:self.max_actions_shown], 1):
            lines.append(action.format_for_prompt(i))
        
        if len(actions) > self.max_actions_shown:
            lines.append(f"... and {len(actions) - self.max_actions_shown} more actions")
        
        return "\n".join(lines)
    
    def _build_response_instructions(self, personality: EntityPersonality) -> str:
        """Build the response format instructions."""
        archetype = personality.archetype
        alignment = personality.alignment.name
        
        return (
            "=== YOUR DECISION ===\n"
            f"Choose the action most consistent with your {alignment} ({archetype}) personality.\n"
            "Consider your tactical situation, your personality traits, and any grudges.\n"
            "\n"
            "Respond with ONLY a JSON object:\n"
            "{\n"
            '  "action": "ACTION_NAME",\n'
            '  "target": "TARGET_NAME or null if no target needed",\n'
            '  "reasoning": "Brief in-character justification (1-2 sentences)"\n'
            "}"
        )
    
    # -------------------------------------------------------------------------
    # Convenience Builders
    # -------------------------------------------------------------------------
    
    def build_simple_prompt(
        self,
        situation: str,
        personality: EntityPersonality,
        options: list[str],
    ) -> str:
        """
        Build a simple decision prompt without full combat state.
        
        Useful for non-combat decisions or quick prototyping.
        """
        lines = [
            f"You are a {personality.alignment.name} character ({personality.archetype}).",
            "",
            personality.format_for_prompt(),
            "",
            "=== SITUATION ===",
            situation,
            "",
            "=== OPTIONS ===",
        ]
        
        for i, option in enumerate(options, 1):
            lines.append(f"{i}. {option}")
        
        lines.extend([
            "",
            "Choose the option most consistent with your personality.",
            "Respond with ONLY a JSON object:",
            "{",
            '  "choice": <number>,',
            '  "reasoning": "Brief in-character justification"',
            "}",
        ])
        
        return "\n".join(lines)

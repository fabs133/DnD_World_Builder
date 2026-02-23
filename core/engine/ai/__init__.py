"""AI-powered entity control for headless game sessions.

This module provides LLM-backed decision making using the alignment-based
personality system (Lawful Good → Chaotic Evil), with a deterministic
heuristic fallback when Ollama is unavailable.
"""

from core.engine.ai.ai_adapter import AIAdapter
from core.engine.ai.heuristic_adapter import HeuristicAIAdapter
from core.engine.ai.ollama_client import OllamaClient, OllamaConfig
from core.engine.ai.action_parser import ActionParser, ParseError
from models.ai.personality import EntityPersonality
from models.ai.alignment import Alignment, LawChaos, GoodEvil
from models.ai.tactical_weights import TacticalWeights
from core.engine.ai.prompt_builder import (
    TacticalPromptBuilder,
    CombatantInfo,
    ActionOption,
    CombatMemory,
)

# Backwards compatibility alias
Personality = EntityPersonality

# Alignment preset instances
LAWFUL_GOOD = EntityPersonality(Alignment.LAWFUL_GOOD)
NEUTRAL_GOOD = EntityPersonality(Alignment.NEUTRAL_GOOD)
CHAOTIC_GOOD = EntityPersonality(Alignment.CHAOTIC_GOOD)
LAWFUL_NEUTRAL = EntityPersonality(Alignment.LAWFUL_NEUTRAL)
TRUE_NEUTRAL = EntityPersonality(Alignment.TRUE_NEUTRAL)
CHAOTIC_NEUTRAL = EntityPersonality(Alignment.CHAOTIC_NEUTRAL)
LAWFUL_EVIL = EntityPersonality(Alignment.LAWFUL_EVIL)
NEUTRAL_EVIL = EntityPersonality(Alignment.NEUTRAL_EVIL)
CHAOTIC_EVIL = EntityPersonality(Alignment.CHAOTIC_EVIL)

# Legacy presets (map to closest alignments)
AGGRESSIVE = EntityPersonality(Alignment.CHAOTIC_EVIL)
DEFENSIVE = EntityPersonality(Alignment.LAWFUL_GOOD)
TACTICAL = EntityPersonality(Alignment.TRUE_NEUTRAL)
BERSERKER = EntityPersonality(Alignment.CHAOTIC_EVIL)

__all__ = [
    # Core adapters
    "AIAdapter",
    "HeuristicAIAdapter",
    # Ollama client
    "OllamaClient",
    "OllamaConfig",
    # Action parsing
    "ActionParser",
    "ParseError",
    # Personality system
    "EntityPersonality",
    "Personality",
    "Alignment",
    "LawChaos",
    "GoodEvil",
    "TacticalWeights",
    # Prompt building
    "TacticalPromptBuilder",
    "CombatantInfo",
    "ActionOption",
    "CombatMemory",
    # Alignment presets
    "LAWFUL_GOOD",
    "NEUTRAL_GOOD",
    "CHAOTIC_GOOD",
    "LAWFUL_NEUTRAL",
    "TRUE_NEUTRAL",
    "CHAOTIC_NEUTRAL",
    "LAWFUL_EVIL",
    "NEUTRAL_EVIL",
    "CHAOTIC_EVIL",
    # Legacy presets
    "AGGRESSIVE",
    "DEFENSIVE",
    "TACTICAL",
    "BERSERKER",
]

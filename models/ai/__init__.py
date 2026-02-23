# models/ai/__init__.py
"""
AI-driven entity behavior system.

This module provides alignment-based personality modeling for game entities,
enabling AI-controlled NPCs to make decisions consistent with D&D alignment.
"""

from .alignment import Alignment, LawChaos, GoodEvil
from .personality import EntityPersonality, ALIGNMENT_BEHAVIORS
from .tactical_weights import TacticalWeights
from .prompt_builder import TacticalPromptBuilder

__all__ = [
    "Alignment",
    "LawChaos",
    "GoodEvil",
    "EntityPersonality",
    "ALIGNMENT_BEHAVIORS",
    "TacticalWeights",
    "TacticalPromptBuilder",
]

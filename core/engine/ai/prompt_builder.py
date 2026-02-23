"""Re-export prompt builder from models.ai for backwards compatibility.

The canonical implementation is in models/ai/prompt_builder.py.
This module exists for import convenience in the engine.
"""

from models.ai.prompt_builder import (
    TacticalPromptBuilder,
    CombatantInfo,
    ActionOption,
    CombatMemory,
)

__all__ = [
    "TacticalPromptBuilder",
    "CombatantInfo", 
    "ActionOption",
    "CombatMemory",
]

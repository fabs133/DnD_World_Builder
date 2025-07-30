"""
This module defines preset triggers for different entity types in the game.

Each preset is a list of Trigger objects, specifying the event, condition, and reaction.

Attributes
----------
trigger_presets : dict
    A dictionary mapping entity types to lists of Trigger presets.
"""

from core.gameCreation.trigger import Trigger
from models.flow.reaction.reactions_list import ApplyDamage as apply_damage
from models.flow.condition.condition_list import AlwaysTrue as always_true
from models.flow.condition.condition_list import PerceptionCheck as perception_check
from models.flow.reaction.reactions_list import AlertGamemaster as alert_gamemaster

#: Preset triggers for different entity types.
#: 
#: Keys are entity types (str), values are lists of Trigger objects.
trigger_presets = {
    "player": [],
    
    "npc": [
        Trigger(
            "TALKED_TO",
            always_true,
            alert_gamemaster
        ),
    ],

    "enemy": [
        Trigger(
            "PLAYER_IN_RANGE",
            (10),
            apply_damage("slashing", 1)
        ),
    ],

    "trap": [
        Trigger(
            "STEPPED_ON",
            perception_check(12),
            apply_damage("piercing", 6)
        ),
    ],

    "object": [],
}

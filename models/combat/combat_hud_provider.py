"""Combat HUD view model provider.

Pure Python — computes role-specific views of combat state for the UI.
Zero PyQt5 dependency.
"""

from __future__ import annotations

from core.constants import DEFAULT_SPEED_FT

from typing import List

from models.combat.combatant import Combatant, CombatantFaction
from models.combat.combat_instance import CombatInstance


class CombatHUDProvider:
    """Computes role-specific views of combat state."""

    @staticmethod
    def get_initiative_display(
        combatants: List[Combatant],
        viewer_role: str,
        viewer_entity_name: str = "",
        current_turn_index: int = 0,
    ) -> list[dict]:
        """Build the initiative tracker display data.

        DM sees exact HP. Players see health categories.

        :param combatants: All combatants in initiative order.
        :param viewer_role: ``"dm"`` or ``"player"``.
        :param viewer_entity_name: The player's entity name (for ``is_you``).
        :param current_turn_index: Index of the current combatant.
        """
        entries = []
        for i, c in enumerate(combatants):
            entry = {
                "name": c.name,
                "faction": c.faction.value,
                "initiative": c.initiative,
                "is_current_turn": i == current_turn_index,
                "is_conscious": c.is_conscious,
                "conditions": list(c.conditions),
            }

            if viewer_role == "dm":
                entry["hp"] = c.hp
                entry["hp_max"] = c.hp_max
                entry["armor_class"] = getattr(c.entity, "armor_class", 10)
            else:
                entry["health_category"] = c.health_category
                entry["is_you"] = c.name == viewer_entity_name

            entries.append(entry)
        return entries

    @staticmethod
    def get_action_bar(
        combatant: Combatant,
        combat_instance: CombatInstance,
    ) -> dict:
        """Build the action bar for the active combatant's turn.

        :param combatant: The combatant whose turn it is.
        :param combat_instance: The live combat state.
        """
        actions = []
        if not combatant.action_used:
            actions.extend([
                {"id": "attack", "label": "Attack", "type": "action", "enabled": True},
                {"id": "cast_spell", "label": "Cast Spell", "type": "action", "enabled": True},
                {"id": "dash", "label": "Dash", "type": "action", "enabled": True},
                {"id": "dodge", "label": "Dodge", "type": "action", "enabled": True},
                {"id": "disengage", "label": "Disengage", "type": "action", "enabled": True},
                {"id": "help", "label": "Help", "type": "action", "enabled": True},
            ])

        bonus_actions = []
        if not combatant.bonus_action_used:
            bonus_actions.append(
                {"id": "bonus", "label": "Bonus Action", "type": "bonus", "enabled": True}
            )

        return {
            "movement_remaining": combatant.movement_remaining,
            "movement_max": getattr(combatant.entity, "speed", DEFAULT_SPEED_FT),
            "actions": actions,
            "bonus_actions": bonus_actions,
            "reaction_available": not combatant.reaction_used,
            "is_your_turn": True,
        }

    @staticmethod
    def get_enemy_stat_block(combatant: Combatant) -> dict:
        """Build the DM-only enemy stat block.

        :param combatant: The enemy combatant.
        """
        entity = combatant.entity
        return {
            "name": combatant.name,
            "ac": getattr(entity, "armor_class", 10),
            "hp": combatant.hp,
            "hp_max": combatant.hp_max,
            "speed": getattr(entity, "speed", DEFAULT_SPEED_FT),
            "conditions": list(combatant.conditions),
            "faction": combatant.faction.value,
        }

    @staticmethod
    def get_combat_summary(combat_instance: CombatInstance) -> dict:
        """Build the round/turn summary display.

        :param combat_instance: The live combat state.
        """
        current = combat_instance.current_combatant
        return {
            "round_number": combat_instance.round_number,
            "current_combatant_name": current.name if current else "",
            "total_combatants": len(combat_instance.combatants),
            "active_combatants": len(combat_instance.active_combatants),
            "state": combat_instance.state.value,
        }

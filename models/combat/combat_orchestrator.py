"""Combat lifecycle orchestrator.

Wraps :class:`~core.engine.game_session.GameSession` with encounter-specific
lifecycle: setup phase, initiative rolling, surprise handling, and end-combat
resolution. All turn execution delegates to the existing GameSession.
"""

from __future__ import annotations

import random
from typing import Any, List, Optional, Tuple

from core.events import (
    COMBAT_ENDED, COMBAT_STARTED, ENTITY_DAMAGED, ENTITY_DIED,
    INITIATIVE_ROLLED, ROUND_STARTED, TURN_STARTED,
)
from core.logger import app_logger
from models.combat.combat_instance import CombatInstance, CombatState
from models.combat.combatant import Combatant, CombatantFaction


class CombatOrchestrator:
    """Drives a combat encounter through its lifecycle.

    Delegates turn execution to GameSession (multi-action turns,
    EventBus, ActionExecutor). Adds setup, initiative, surprise,
    and end-combat phases.
    """

    def __init__(self, combat_instance: CombatInstance, gamemaster: Any):
        self.instance = combat_instance
        self.gamemaster = gamemaster
        self._session = None  # Created during begin_combat

    def start_setup(self) -> None:
        """Transition to SETUP. DM can adjust positions."""
        self.instance.state = CombatState.SETUP
        self.instance.log_event("combat_setup", template=self.instance.template_name)
        app_logger.info(f"Combat setup: {self.instance.template_name}")

        from core.gameCreation.event_bus import EventBus
        EventBus.emit(COMBAT_STARTED, {
            "instance_id": self.instance.instance_id,
            "template_name": self.instance.template_name,
        })

    def roll_initiative(self, seed: int | None = None) -> list[dict]:
        """Roll initiative for all combatants and sort descending.

        Uses d20 + DEX modifier. Returns the roll breakdown.
        """
        self.instance.state = CombatState.INITIATIVE
        rng = random.Random(seed)
        rolls = []

        for combatant in self.instance.combatants:
            dex = getattr(combatant.entity, "stats", {}).get("Dexterity", 10)
            dex_mod = (dex - 10) // 2
            roll = rng.randint(1, 20)
            total = roll + dex_mod
            combatant.initiative = total

            rolls.append({
                "name": combatant.name,
                "roll": roll,
                "modifier": dex_mod,
                "total": total,
                "faction": combatant.faction.value,
            })

        # Sort combatants by initiative (descending), tiebreak by DEX
        self.instance.combatants.sort(
            key=lambda c: (
                c.initiative,
                getattr(c.entity, "stats", {}).get("Dexterity", 10),
            ),
            reverse=True,
        )

        self.instance.log_event("initiative_rolled", rolls=rolls)
        app_logger.info(
            f"Initiative rolled: {', '.join(r['name'] + '=' + str(r['total']) for r in rolls)}"
        )

        from core.gameCreation.event_bus import EventBus
        EventBus.emit(INITIATIVE_ROLLED, {"rolls": rolls})

        return rolls

    def reorder_initiative(self, name: str, new_index: int) -> None:
        """DM manually reorders a combatant (for tie resolution)."""
        combatant = next((c for c in self.instance.combatants if c.name == name), None)
        if combatant is None:
            return
        self.instance.combatants.remove(combatant)
        self.instance.combatants.insert(new_index, combatant)

    def apply_surprise(self, surprised_names: list[str]) -> None:
        """Mark specific combatants as surprised."""
        for combatant in self.instance.combatants:
            if combatant.name in surprised_names:
                combatant.surprised = True
                self.instance.log_event(
                    "condition_applied",
                    entity=combatant.name,
                    condition="surprised",
                )

    def begin_combat(self) -> None:
        """Transition to ACTIVE. Create GameSession for turn execution."""
        self.instance.state = CombatState.ACTIVE
        self.instance.round_number = 1
        self.instance.current_turn_index = 0

        # Reset all combatants for the first turn
        for combatant in self.instance.combatants:
            combatant.reset_turn()

        self.instance.log_event("combat_started_active", round_number=1)
        app_logger.info(f"Combat active: round 1")

        from core.gameCreation.event_bus import EventBus
        EventBus.emit(ROUND_STARTED, {"round": 1})

        current = self.instance.current_combatant
        if current:
            # Skip surprised combatants in round 1
            if current.surprised:
                self.instance.log_event(
                    "turn_skipped", entity=current.name, reason="surprised"
                )
                self.end_turn()
            else:
                EventBus.emit(TURN_STARTED, {
                    "entity": current.name,
                    "round": 1,
                })

    def end_turn(self) -> None:
        """Advance to next combatant, or next round if all have gone."""
        current = self.instance.current_combatant
        if current:
            self.instance.log_event("turn_ended", entity=current.name)

        self.instance.current_turn_index += 1

        # Wrap to next round
        if self.instance.current_turn_index >= len(self.instance.combatants):
            self.instance.current_turn_index = 0
            self.instance.round_number += 1
            # Clear surprise after round 1
            for c in self.instance.combatants:
                c.surprised = False

            from core.gameCreation.event_bus import EventBus
            EventBus.emit(ROUND_STARTED, {"round": self.instance.round_number})
            self.instance.log_event(
                "round_started", round_number=self.instance.round_number
            )

        # Reset the new combatant's turn resources
        next_combatant = self.instance.current_combatant
        if next_combatant:
            next_combatant.reset_turn()

            # Skip surprised combatants in round 1
            if next_combatant.surprised and self.instance.round_number == 1:
                self.instance.log_event(
                    "turn_skipped", entity=next_combatant.name, reason="surprised"
                )
                self.end_turn()
                return

            from core.gameCreation.event_bus import EventBus
            EventBus.emit(TURN_STARTED, {
                "entity": next_combatant.name,
                "round": self.instance.round_number,
            })

    def apply_damage(
        self, target_name: str, amount: int, damage_type: str = ""
    ) -> dict:
        """Apply damage to a combatant."""
        target = next(
            (c for c in self.instance.combatants if c.name == target_name), None
        )
        if target is None:
            return {"target": target_name, "damage": 0, "remaining_hp": 0, "died": False}

        old_hp = target.hp
        if hasattr(target.entity, "take_damage"):
            target.entity.take_damage(amount, damage_type)
        else:
            target.entity.hp = max(0, target.entity.hp - amount)

        died = target.hp <= 0 and old_hp > 0

        self.instance.log_event(
            "entity_damaged",
            target=target_name,
            damage=amount,
            damage_type=damage_type,
            remaining_hp=target.hp,
            died=died,
        )

        if died:
            from core.gameCreation.event_bus import EventBus
            EventBus.emit(ENTITY_DIED, {
                "entity": target_name,
                "position": target.position,
            })

        return {
            "target": target_name,
            "damage": amount,
            "remaining_hp": target.hp,
            "died": died,
        }

    def check_end_conditions(self) -> str | None:
        """Check if combat should end.

        Returns ``"victory"`` if all enemies down, ``"defeat"`` if all
        players down, or ``None`` if combat continues.
        """
        players_alive = any(c.is_conscious for c in self.instance.players)
        enemies_alive = any(c.is_conscious for c in self.instance.enemies)

        if not enemies_alive:
            return "victory"
        if not players_alive:
            return "defeat"
        return None

    def end_combat(self, outcome: str = "victory") -> dict:
        """Resolve combat. Transition to ENDED."""
        self.instance.state = CombatState.ENDED

        summary = {
            "outcome": outcome,
            "rounds": self.instance.round_number,
            "casualties": [
                c.name for c in self.instance.combatants if not c.is_conscious
            ],
            "survivors": [
                c.name for c in self.instance.combatants if c.is_conscious
            ],
        }

        self.instance.log_event("combat_ended", **summary)
        app_logger.info(f"Combat ended: {outcome} after {self.instance.round_number} rounds")

        from core.gameCreation.event_bus import EventBus
        EventBus.emit(COMBAT_ENDED, summary)

        return summary

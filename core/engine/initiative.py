"""D&D 5e initiative tracker with deterministic tiebreaking."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


@dataclass
class InitiativeEntry:
    """One entity's initiative info."""

    entity_name: str
    roll: int
    dex_modifier: int
    tiebreaker: int
    entity_ref: Any


class InitiativeTracker:
    """Manages D&D-style initiative order with deterministic seeding.

    Sorting: primary by roll desc, secondary by dex desc, tertiary by tiebreaker desc.
    """

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)
        self._entries: list[InitiativeEntry] = []
        self._current_index: int = 0
        self._round_number: int = 1

    def roll_initiative(self, entities: list) -> list[InitiativeEntry]:
        """Roll initiative for all entities. Returns sorted order."""
        self._entries = []
        for entity in entities:
            dex_mod = _get_dex_modifier(entity)
            roll = self._rng.randint(1, 20) + dex_mod
            tiebreaker = self._rng.randint(1, 1000)
            self._entries.append(InitiativeEntry(
                entity_name=entity.name,
                roll=roll,
                dex_modifier=dex_mod,
                tiebreaker=tiebreaker,
                entity_ref=entity,
            ))
        self._sort()
        self._current_index = 0
        self._round_number = 1
        return list(self._entries)

    def add_entity(self, entity, roll_override: int | None = None) -> InitiativeEntry:
        """Add an entity mid-combat."""
        dex_mod = _get_dex_modifier(entity)
        roll = roll_override if roll_override is not None else (self._rng.randint(1, 20) + dex_mod)
        tiebreaker = self._rng.randint(1, 1000)
        entry = InitiativeEntry(
            entity_name=entity.name,
            roll=roll,
            dex_modifier=dex_mod,
            tiebreaker=tiebreaker,
            entity_ref=entity,
        )
        self._entries.append(entry)
        self._sort()
        return entry

    def remove_entity(self, entity_name: str) -> None:
        """Remove entity from initiative."""
        old_current_name = self.current_entity.entity_name if self._entries else None
        self._entries = [e for e in self._entries if e.entity_name != entity_name]
        if not self._entries:
            self._current_index = 0
            return
        if old_current_name and old_current_name != entity_name:
            for i, e in enumerate(self._entries):
                if e.entity_name == old_current_name:
                    self._current_index = i
                    return
        self._current_index = min(self._current_index, len(self._entries) - 1)

    @property
    def current_entity(self) -> InitiativeEntry | None:
        """The entity whose turn it currently is."""
        if not self._entries:
            return None
        return self._entries[self._current_index]

    @property
    def round_number(self) -> int:
        return self._round_number

    def next_turn(self) -> InitiativeEntry | None:
        """Advance to the next entity's turn, incrementing round if needed."""
        if not self._entries:
            return None
        self._current_index += 1
        if self._current_index >= len(self._entries):
            self._current_index = 0
            self._round_number += 1
        return self._entries[self._current_index]

    def get_order(self) -> list[str]:
        """Return entity names in initiative order."""
        return [e.entity_name for e in self._entries]

    def reset(self) -> None:
        """Clear all entries and reset round counter."""
        self._entries = []
        self._current_index = 0
        self._round_number = 1

    def _sort(self) -> None:
        self._entries.sort(key=lambda e: (e.roll, e.dex_modifier, e.tiebreaker), reverse=True)


def _get_dex_modifier(entity) -> int:
    """Extract Dexterity modifier from an entity."""
    stats = getattr(entity, "stats", {})
    dex = stats.get("Dexterity", stats.get("dexterity", stats.get("DEX", 10)))
    if isinstance(dex, dict):
        dex = dex.get("score", dex.get("value", 10))
    return (int(dex) - 10) // 2

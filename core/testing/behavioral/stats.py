"""Behavioral event tracking and statistical aggregation."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto


class BehaviorEvent(Enum):
    """Trackable events during combat."""

    # Combat
    ATTACKED = auto()
    DEALT_DAMAGE = auto()
    TOOK_DAMAGE = auto()
    KILLED_ENEMY = auto()
    DIED = auto()

    # Target selection
    TARGETED_WEAKEST = auto()
    TARGETED_STRONGEST = auto()
    TARGETED_NEAREST = auto()
    TARGETED_GRUDGE = auto()
    TARGETED_RANDOM = auto()

    # Ally interaction
    ALLY_THREATENED = auto()
    PROTECTED_ALLY = auto()
    HEALED_ALLY = auto()
    IGNORED_DYING_ALLY = auto()
    BETRAYED_ALLY = auto()

    # Self-preservation
    CONSIDERED_FLEEING = auto()
    FLED_COMBAT = auto()
    STAYED_DESPITE_DANGER = auto()

    # Mercy
    COULD_EXECUTE_DOWNED = auto()
    EXECUTED_DOWNED = auto()
    SPARED_DOWNED = auto()

    # Honor
    ATTACKED_FLEEING = auto()
    ACCEPTED_SURRENDER = auto()
    USED_DIRTY_TRICK = auto()
    FOUGHT_HONORABLY = auto()

    # Coordination
    FOCUS_FIRED = auto()
    BROKE_FORMATION = auto()
    FOLLOWED_ORDERS = auto()

    # Chaos / Unpredictability
    CHANGED_TARGET_MID_COMBAT = auto()
    DID_SOMETHING_SUBOPTIMAL = auto()


@dataclass
class EntityRunStats:
    """Stats for a single entity in a single run."""

    entity_name: str
    alignment: str
    run_id: int
    seed: int
    events: list[tuple[int, BehaviorEvent, dict]] = field(default_factory=list)

    damage_dealt: int = 0
    damage_taken: int = 0
    healing_done: int = 0
    kills: int = 0
    died: bool = False
    rounds_survived: int = 0
    final_hp_percent: float = 0.0

    def record(self, round_num: int, event: BehaviorEvent, **metadata) -> None:
        """Record a behavioral event with optional metadata."""
        self.events.append((round_num, event, metadata))

    def count(self, event: BehaviorEvent) -> int:
        """Count occurrences of a specific event."""
        return sum(1 for _, e, _ in self.events if e is event)

    def has(self, event: BehaviorEvent) -> bool:
        """Check if an event occurred at least once."""
        return any(e is event for _, e, _ in self.events)


@dataclass
class BehaviorStats:
    """Aggregated stats for one entity across N runs."""

    entity_name: str
    alignment: str
    runs: list[EntityRunStats] = field(default_factory=list)

    @property
    def run_count(self) -> int:
        return len(self.runs)

    @property
    def survival_rate(self) -> float:
        if not self.runs:
            return 0.0
        return sum(1 for r in self.runs if not r.died) / len(self.runs)

    @property
    def avg_damage_dealt(self) -> float:
        if not self.runs:
            return 0.0
        return sum(r.damage_dealt for r in self.runs) / len(self.runs)

    @property
    def avg_kills(self) -> float:
        if not self.runs:
            return 0.0
        return sum(r.kills for r in self.runs) / len(self.runs)

    @property
    def flee_rate(self) -> float:
        return self.rate(BehaviorEvent.FLED_COMBAT, BehaviorEvent.CONSIDERED_FLEEING)

    @property
    def mercy_rate(self) -> float:
        return self.rate(BehaviorEvent.SPARED_DOWNED, BehaviorEvent.COULD_EXECUTE_DOWNED)

    @property
    def protect_rate(self) -> float:
        return self.rate(BehaviorEvent.PROTECTED_ALLY, BehaviorEvent.ALLY_THREATENED)

    @property
    def betrayal_rate(self) -> float:
        return self.rate(BehaviorEvent.BETRAYED_ALLY, BehaviorEvent.ALLY_THREATENED)

    @property
    def target_entropy(self) -> float:
        """Shannon entropy of target selection, normalized to [0, 1]."""
        target_events = [
            BehaviorEvent.TARGETED_WEAKEST,
            BehaviorEvent.TARGETED_STRONGEST,
            BehaviorEvent.TARGETED_NEAREST,
            BehaviorEvent.TARGETED_RANDOM,
        ]
        counts = [self.total(e) for e in target_events]
        total = sum(counts)
        if total == 0:
            return 0.0
        probs = [c / total for c in counts if c > 0]
        entropy = -sum(p * math.log2(p) for p in probs)
        max_entropy = math.log2(len(target_events))
        return entropy / max_entropy if max_entropy > 0 else 0.0

    def total(self, event: BehaviorEvent) -> int:
        """Total occurrences of an event across all runs."""
        return sum(r.count(event) for r in self.runs)

    def rate(self, event: BehaviorEvent, opportunity: BehaviorEvent) -> float:
        """Rate of event given opportunity. Returns 0.0 if no opportunities."""
        opp = self.total(opportunity)
        if opp == 0:
            return 0.0
        return self.total(event) / opp

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON output."""
        return {
            "entity_name": self.entity_name,
            "alignment": self.alignment,
            "run_count": self.run_count,
            "survival_rate": round(self.survival_rate, 3),
            "avg_damage_dealt": round(self.avg_damage_dealt, 1),
            "avg_kills": round(self.avg_kills, 2),
            "flee_rate": round(self.flee_rate, 3),
            "mercy_rate": round(self.mercy_rate, 3),
            "protect_rate": round(self.protect_rate, 3),
            "betrayal_rate": round(self.betrayal_rate, 3),
            "target_entropy": round(self.target_entropy, 3),
        }

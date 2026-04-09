"""Quest and objective data model for the quest tracking system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QuestObjective:
    """A single objective within a quest, tracked by a dialogue flag."""

    description: str
    flag_name: str
    completed: bool = False

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "flag_name": self.flag_name,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> QuestObjective:
        return cls(
            description=data["description"],
            flag_name=data["flag_name"],
            completed=data.get("completed", False),
        )


@dataclass
class Quest:
    """A quest with objectives, rewards, and flag-based tracking."""

    quest_id: str
    title: str
    description: str
    giver: str                                     # NPC name who gives the quest
    objectives: list[QuestObjective] = field(default_factory=list)
    rewards: dict = field(default_factory=dict)     # {"gold": 50, "items": [...], "xp": 100}
    status: str = "available"                       # "available" | "active" | "completed" | "failed"
    prerequisite_flags: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """True if all objectives are completed."""
        return all(o.completed for o in self.objectives) if self.objectives else False

    def check_objectives(self, flags: dict[str, bool]) -> bool:
        """Update objective completion from dialogue flags.

        Returns True if any objective status changed.
        """
        changed = False
        for obj in self.objectives:
            was = obj.completed
            obj.completed = flags.get(obj.flag_name, False)
            if obj.completed != was:
                changed = True
        return changed

    def is_available(self, flags: dict[str, bool]) -> bool:
        """True if all prerequisite flags are met."""
        return all(flags.get(f, False) for f in self.prerequisite_flags)

    def to_dict(self) -> dict:
        return {
            "quest_id": self.quest_id,
            "title": self.title,
            "description": self.description,
            "giver": self.giver,
            "objectives": [o.to_dict() for o in self.objectives],
            "rewards": self.rewards,
            "status": self.status,
            "prerequisite_flags": self.prerequisite_flags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Quest:
        return cls(
            quest_id=data["quest_id"],
            title=data["title"],
            description=data["description"],
            giver=data["giver"],
            objectives=[QuestObjective.from_dict(o) for o in data.get("objectives", [])],
            rewards=data.get("rewards", {}),
            status=data.get("status", "available"),
            prerequisite_flags=data.get("prerequisite_flags", []),
        )

"""Quest tracker — manages active quests and checks completion via dialogue flags."""

from __future__ import annotations

from typing import Callable, Optional

from models.quest.quest import Quest


class QuestTracker:
    """Tracks quest state, checks objectives against dialogue flags.

    Parameters
    ----------
    quests : list[Quest]
        All quests for the scenario.
    on_quest_completed : callable, optional
        Called with Quest when all objectives are met.
    """

    def __init__(self, quests: list[Quest],
                 on_quest_completed: Callable[[Quest], None] | None = None):
        self._quests = {q.quest_id: q for q in quests}
        self._on_completed = on_quest_completed

    # ── Public API ───────────────────────────────────────────────

    def get_available(self, flags: dict[str, bool]) -> list[Quest]:
        """Return quests whose prerequisites are met and status is 'available'."""
        return [
            q for q in self._quests.values()
            if q.status == "available" and q.is_available(flags)
        ]

    def get_active(self) -> list[Quest]:
        """Return all quests with status 'active'."""
        return [q for q in self._quests.values() if q.status == "active"]

    def get_completed(self) -> list[Quest]:
        """Return all completed quests."""
        return [q for q in self._quests.values() if q.status == "completed"]

    def get_all(self) -> list[Quest]:
        """Return all quests."""
        return list(self._quests.values())

    def accept_quest(self, quest_id: str) -> bool:
        """Move a quest from 'available' to 'active'."""
        q = self._quests.get(quest_id)
        if q and q.status == "available":
            q.status = "active"
            return True
        return False

    def check_flags(self, flags: dict[str, bool]) -> list[Quest]:
        """Check all active quests against current flags.

        Auto-accepts quests that become available through prerequisite flags.
        Returns list of quests that were just completed.
        """
        newly_completed = []

        # Auto-accept quests whose givers have been talked to
        # (quest flag like "X_quest_accepted" gets set during NPC dialogue)
        for q in list(self._quests.values()):
            if q.status == "available" and q.is_available(flags):
                # Check if the first objective flag is already set
                # (player accepted quest during dialogue)
                if q.objectives and flags.get(q.objectives[0].flag_name, False):
                    q.status = "active"

        # Update objectives for active quests
        for q in list(self._quests.values()):
            if q.status != "active":
                continue
            changed = q.check_objectives(flags)
            if changed and q.is_complete:
                q.status = "completed"
                newly_completed.append(q)
                if self._on_completed:
                    self._on_completed(q)

        return newly_completed

    def get_quest(self, quest_id: str) -> Optional[Quest]:
        return self._quests.get(quest_id)

    # ── Serialization ────────────────────────────────────────────

    def to_dict(self) -> list[dict]:
        return [q.to_dict() for q in self._quests.values()]

    def restore_state(self, saved: list[dict]) -> None:
        """Restore quest statuses from saved state."""
        saved_map = {d["quest_id"]: d for d in saved}
        for qid, q in self._quests.items():
            if qid in saved_map:
                q.status = saved_map[qid].get("status", q.status)
                for i, obj_data in enumerate(saved_map[qid].get("objectives", [])):
                    if i < len(q.objectives):
                        q.objectives[i].completed = obj_data.get("completed", False)

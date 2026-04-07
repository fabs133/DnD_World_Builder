"""Role-based information filtering for play mode. No Qt imports."""

from __future__ import annotations

from core.engine.play_state import PlayerRole
from models.entities.entity_type import EntityType


class InfoFilter:
    """Determines what information is visible to the current role.

    Pure data — no Qt. UI components call these methods to decide
    what to display.
    """

    def __init__(self, role: PlayerRole,
                 controlled_entity_name: str | None = None,
                 party_names: frozenset[str] = frozenset()):
        self._role = role
        self._controlled = controlled_entity_name
        self._party = party_names

    def can_see_hp(self, entity_name: str) -> bool:
        """Should exact HP be shown for this entity?"""
        if self._role in (PlayerRole.DM, PlayerRole.SPECTATOR):
            return True
        return entity_name in self._party

    def can_see_stats(self, entity_name: str) -> bool:
        """Should AC, abilities, spells, inventory be shown?

        DM sees all. Spectator sees party. Player sees own character only.
        """
        if self._role == PlayerRole.DM:
            return True
        if self._role == PlayerRole.SPECTATOR:
            return entity_name in self._party
        return entity_name == self._controlled

    @staticmethod
    def health_category(hp: int, max_hp: int) -> str:
        """Compute health category from HP ratio.

        Used for player-role initiative display instead of exact numbers.
        """
        if max_hp <= 0:
            return "unconscious"
        ratio = hp / max_hp
        if hp <= 0:
            return "unconscious"
        if ratio > 0.75:
            return "healthy"
        if ratio > 0.50:
            return "wounded"
        if ratio > 0.25:
            return "bloodied"
        return "near_death"

    def should_fog(self, role: PlayerRole | None = None) -> bool:
        """Should fog of war be active?"""
        r = role or self._role
        return r != PlayerRole.DM

    def get_vision_entities(self, entities, controlled_name: str | None = None):
        """Return entities whose positions drive fog of war.

        Player: only their character. Spectator: all players.
        DM: empty (fog disabled).
        """
        if self._role == PlayerRole.DM:
            return []  # Fog disabled
        name = controlled_name or self._controlled
        if self._role == PlayerRole.PLAYER and name:
            return [e for e in entities if getattr(e, "name", "") == name]
        # Spectator: all player entities
        return [e for e in entities
                if getattr(e, "entity_type", "") == EntityType.PLAYER]

    def can_control(self, entity_name: str) -> bool:
        """Can the current role take actions for this entity?"""
        if self._role == PlayerRole.SPECTATOR:
            return False
        if self._role == PlayerRole.PLAYER:
            return entity_name == self._controlled
        return True  # DM can control any entity

    def initiative_role(self) -> str:
        """Return the role string for InitiativePanel.set_role()."""
        if self._role in (PlayerRole.DM, PlayerRole.SPECTATOR):
            return "dm"
        return "player"

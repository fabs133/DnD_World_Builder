"""Structural protocol defining the minimum entity interface.

Any object that satisfies this protocol can be used wherever the engine
expects an "entity" — including :class:`GameEntity`, ``DemoEntity``,
and test doubles.  Using ``getattr(entity, "speed", 30)`` defensively
is no longer necessary when the caller declares it accepts
``EntityLike``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EntityLike(Protocol):
    """Minimum interface for objects that act as game entities."""

    name: str
    entity_type: str
    hp: int
    max_hp: int
    armor_class: int
    speed: int
    position: tuple[int, int] | None
    conditions: list
    stats: dict

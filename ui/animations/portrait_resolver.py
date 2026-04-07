"""Portrait resolver — selects the correct health-state portrait for an entity.

Pure logic, no Qt imports.  Health thresholds align with D&D convention:
- healthy:  > 75% HP
- wounded:  50–75% HP
- bloodied: 25–50% HP (D&D "bloodied" is traditionally 50%)
- critical: < 25% HP
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


_THRESHOLDS = [
    (0.75, "healthy"),
    (0.50, "wounded"),
    (0.25, "bloodied"),
    (0.00, "critical"),
]


def health_state(hp_percent: float) -> str:
    """Return the health state string for a given HP percentage (0.0–1.0)."""
    for threshold, state in _THRESHOLDS:
        if hp_percent > threshold:
            return state
    return "critical"


def resolve_portrait(entity: Any, base_dir: str | Path = "") -> str | None:
    """Return the filesystem path to the correct portrait for the entity.

    Resolution order:
    1. ``entity.portraits[health_state]`` — if the dict has a matching key
    2. ``entity.image_path`` — single-image fallback
    3. ``None`` — CombatTileItem draws the existing colored circle

    :param entity: A GameEntity (or anything with hp_percent, portraits, image_path).
    :param base_dir: Base directory for resolving relative portrait paths.
    """
    hp_pct = getattr(entity, "hp_percent", 1.0)
    state = health_state(hp_pct)

    portraits = getattr(entity, "portraits", {})
    if portraits:
        for try_state in _state_fallback_order(state):
            path = portraits.get(try_state)
            if path:
                return _resolve_path(path, base_dir)

    image_path = getattr(entity, "image_path", None)
    if image_path:
        return _resolve_path(image_path, base_dir)

    return None


def _state_fallback_order(state: str) -> list[str]:
    """Return the state plus fallbacks (critical → bloodied → wounded → healthy)."""
    all_states = ["critical", "bloodied", "wounded", "healthy"]
    try:
        idx = all_states.index(state)
    except ValueError:
        return [state, "healthy"]
    return all_states[idx:] + all_states[:idx]


def _resolve_path(path: str, base_dir: str | Path) -> str:
    if not base_dir:
        return path
    p = Path(path)
    if p.is_absolute():
        return str(p)
    return str(Path(base_dir) / p)

"""Game-wide numeric constants.

Centralises magic numbers that were previously scattered across files.
Import the constant you need rather than repeating the raw number.
"""

# -- D&D 5e defaults ---------------------------------------------------------
DEFAULT_SPEED_FT: int = 30
"""Standard walking speed in feet (PHB p.14)."""

FEET_PER_TILE: int = 5
"""Each grid tile represents 5 feet of distance (PHB p.192)."""

DEFAULT_VISION_RADIUS: int = 4
"""Fog-of-war vision range in tiles for entities without an explicit
``vision_range`` attribute.  Equivalent to 20 ft (4 * 5 ft)."""

INITIATIVE_TIEBREAKER_RANGE: int = 1000
"""Upper bound for random tiebreaker in initiative rolls."""

# -- UI tile sizes (pixels) ---------------------------------------------------
COMBAT_TILE_SIZE_PX: int = 36
"""Tile size on the play-mode combat map."""

MINIMAP_TILE_SIZE_PX: int = 20
"""Tile size on the play-mode sidebar mini-map."""

EDITOR_TILE_SIZE_PX: int = 50
"""Default tile size in the map editor."""

# -- Limits -------------------------------------------------------------------
SRD_CREATURE_LOAD_LIMIT: int = 100
"""Maximum SRD creatures loaded into the entity palette at once."""

EVENT_BRIDGE_THROTTLE_MS: int = 100
"""Minimum interval between network state-delta broadcasts (ms)."""

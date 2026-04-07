"""Play session state machine and role definitions. No Qt imports."""

from enum import Enum, auto


class PlayState(Enum):
    """States the play session transitions through."""
    SETUP       = auto()
    INTRO       = auto()
    EXPLORATION = auto()
    COMBAT      = auto()
    ENDED       = auto()


class PlayerRole(Enum):
    """How the user participates in the session."""
    PLAYER    = "player"     # Controls one character, limited info
    DM        = "dm"         # Sees all, controls flow, observer by default
    SPECTATOR = "spectator"  # Watches AI play, full visibility, no controls


class DMAutomation(Enum):
    """Who does the AI control during combat? DM-only setting."""
    ALL_AUTO     = auto()  # AI controls everyone — DM watches (simulation mode)
    ENEMIES_ONLY = auto()  # AI controls enemies/NPCs, DM picks party actions (default)
    MANUAL       = auto()  # DM controls everyone — pure tabletop mode

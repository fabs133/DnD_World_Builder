# models/ai/alignment.py
"""
D&D Alignment System.

The classic 3x3 alignment grid that every D&D player knows and loves.
Maps directly to tactical behavior weights for AI decision-making.
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tactical_weights import TacticalWeights


class LawChaos(Enum):
    """The Law-Chaos axis of alignment."""
    LAWFUL = "lawful"
    NEUTRAL = "neutral"
    CHAOTIC = "chaotic"


class GoodEvil(Enum):
    """The Good-Evil axis of alignment."""
    GOOD = "good"
    NEUTRAL = "neutral"
    EVIL = "evil"


@dataclass(frozen=True)
class Alignment:
    """
    A D&D alignment combining the two moral axes.
    
    Examples:
        >>> Alignment(LawChaos.CHAOTIC, GoodEvil.EVIL)
        Alignment(law_chaos=<LawChaos.CHAOTIC>, good_evil=<GoodEvil.EVIL>)
        >>> Alignment.LAWFUL_GOOD
        Alignment(law_chaos=<LawChaos.LAWFUL>, good_evil=<GoodEvil.GOOD>)
    """
    
    law_chaos: LawChaos
    good_evil: GoodEvil
    
    # -------------------------------------------------------------------------
    # Named Constructors (the classic 9)
    # -------------------------------------------------------------------------
    
    @classmethod
    @property
    def LAWFUL_GOOD(cls) -> Alignment:
        """The Protector — follows the code, shields the innocent."""
        return cls(LawChaos.LAWFUL, GoodEvil.GOOD)
    
    @classmethod
    @property
    def NEUTRAL_GOOD(cls) -> Alignment:
        """The Benefactor — helps those in need, flexible in approach."""
        return cls(LawChaos.NEUTRAL, GoodEvil.GOOD)
    
    @classmethod
    @property
    def CHAOTIC_GOOD(cls) -> Alignment:
        """The Rebel — does the right thing, rules be damned."""
        return cls(LawChaos.CHAOTIC, GoodEvil.GOOD)
    
    @classmethod
    @property
    def LAWFUL_NEUTRAL(cls) -> Alignment:
        """The Soldier — orders are orders."""
        return cls(LawChaos.LAWFUL, GoodEvil.NEUTRAL)
    
    @classmethod
    @property
    def TRUE_NEUTRAL(cls) -> Alignment:
        """The Pragmatist — whatever works."""
        return cls(LawChaos.NEUTRAL, GoodEvil.NEUTRAL)
    
    @classmethod
    @property
    def CHAOTIC_NEUTRAL(cls) -> Alignment:
        """The Free Spirit — don't fence me in."""
        return cls(LawChaos.CHAOTIC, GoodEvil.NEUTRAL)
    
    @classmethod
    @property
    def LAWFUL_EVIL(cls) -> Alignment:
        """The Tyrant — power through dominion."""
        return cls(LawChaos.LAWFUL, GoodEvil.EVIL)
    
    @classmethod
    @property
    def NEUTRAL_EVIL(cls) -> Alignment:
        """The Mercenary — nothing personal, just business."""
        return cls(LawChaos.NEUTRAL, GoodEvil.EVIL)
    
    @classmethod
    @property
    def CHAOTIC_EVIL(cls) -> Alignment:
        """The Agent of Chaos — watch it all burn."""
        return cls(LawChaos.CHAOTIC, GoodEvil.EVIL)
    
    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------
    
    @property
    def name(self) -> str:
        """
        Human-readable alignment name.
        
        Returns 'True Neutral' for neutral/neutral, otherwise 'Lawful Good', etc.
        """
        if self.law_chaos == LawChaos.NEUTRAL and self.good_evil == GoodEvil.NEUTRAL:
            return "True Neutral"
        return f"{self.law_chaos.value.title()} {self.good_evil.value.title()}"
    
    @property
    def short_code(self) -> str:
        """
        Two-letter code for compact display.
        
        Examples: LG, NG, CG, LN, TN, CN, LE, NE, CE
        """
        law_map = {LawChaos.LAWFUL: "L", LawChaos.NEUTRAL: "N", LawChaos.CHAOTIC: "C"}
        good_map = {GoodEvil.GOOD: "G", GoodEvil.NEUTRAL: "N", GoodEvil.EVIL: "E"}
        
        if self.law_chaos == LawChaos.NEUTRAL and self.good_evil == GoodEvil.NEUTRAL:
            return "TN"  # True Neutral
        
        return law_map[self.law_chaos] + good_map[self.good_evil]
    
    @property 
    def archetype(self) -> str:
        """The iconic archetype name for this alignment."""
        from .personality import ALIGNMENT_BEHAVIORS
        key = (self.law_chaos.value, self.good_evil.value)
        return ALIGNMENT_BEHAVIORS.get(key, {}).get("archetype", "Unknown")
    
    # -------------------------------------------------------------------------
    # Tactical Weight Generation
    # -------------------------------------------------------------------------
    
    def to_tactical_weights(self) -> "TacticalWeights":
        """
        Convert alignment to tactical behavior weights.
        
        Returns a TacticalWeights instance with values influenced by both axes.
        """
        from .tactical_weights import TacticalWeights
        
        # Start with neutral baseline
        weights = {
            "coordination": 0.5,
            "predictability": 0.5,
            "ally_protection": 0.5,
            "mercy": 0.5,
            "self_sacrifice": 0.5,
            "target_priority": 0.5,  # 0 = easy kills, 1 = threats first
            "honor": 0.5,
            "aggression": 0.5,
            "flee_threshold": 0.3,   # HP% at which to consider fleeing
        }
        
        # Law/Chaos axis adjustments
        if self.law_chaos == LawChaos.LAWFUL:
            weights["coordination"] = 0.8
            weights["predictability"] = 0.8
            weights["honor"] = 0.75
            weights["flee_threshold"] = 0.2  # Lawful holds the line longer
        elif self.law_chaos == LawChaos.CHAOTIC:
            weights["coordination"] = 0.2
            weights["predictability"] = 0.2
            weights["honor"] = 0.3
            weights["flee_threshold"] = 0.4  # Chaotic more likely to bail
        
        # Good/Evil axis adjustments
        if self.good_evil == GoodEvil.GOOD:
            weights["ally_protection"] = 0.85
            weights["mercy"] = 0.8
            weights["self_sacrifice"] = 0.7
            weights["target_priority"] = 0.75  # Prioritize threats to allies
            weights["aggression"] = 0.4  # Defensive posture
        elif self.good_evil == GoodEvil.EVIL:
            weights["ally_protection"] = 0.2
            weights["mercy"] = 0.1
            weights["self_sacrifice"] = 0.1
            weights["target_priority"] = 0.25  # Pick off the weak
            weights["aggression"] = 0.7  # Aggressive posture
        
        # Special cases for extreme alignments
        if self.law_chaos == LawChaos.LAWFUL and self.good_evil == GoodEvil.EVIL:
            # Tyrant: will sacrifice minions, won't retreat (shows weakness)
            weights["ally_protection"] = 0.1  # Uses minions as pawns
            weights["flee_threshold"] = 0.1   # Won't flee
            weights["aggression"] = 0.6
        
        if self.law_chaos == LawChaos.CHAOTIC and self.good_evil == GoodEvil.EVIL:
            # Agent of Chaos: unpredictable, cruel, enjoys suffering
            weights["mercy"] = 0.0
            weights["predictability"] = 0.1
            weights["aggression"] = 0.85
        
        if self.law_chaos == LawChaos.CHAOTIC and self.good_evil == GoodEvil.GOOD:
            # Rebel: dramatic, heroic, charges in recklessly
            weights["self_sacrifice"] = 0.8
            weights["aggression"] = 0.6
            weights["flee_threshold"] = 0.15  # Never back down from injustice
        
        return TacticalWeights(**weights)
    
    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "law_chaos": self.law_chaos.value,
            "good_evil": self.good_evil.value,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> Alignment:
        """Deserialize from dictionary."""
        return cls(
            law_chaos=LawChaos(data["law_chaos"]),
            good_evil=GoodEvil(data["good_evil"]),
        )
    
    @classmethod
    def from_string(cls, s: str) -> Alignment:
        """
        Parse from string like 'chaotic evil' or 'CE'.
        
        Accepts:
            - Full names: 'lawful good', 'chaotic evil', 'true neutral'
            - Short codes: 'LG', 'CE', 'TN'
            - Mixed case: 'Lawful Good', 'CHAOTIC EVIL'
        """
        s = s.strip().lower()
        
        # Handle short codes
        code_map = {
            "lg": (LawChaos.LAWFUL, GoodEvil.GOOD),
            "ng": (LawChaos.NEUTRAL, GoodEvil.GOOD),
            "cg": (LawChaos.CHAOTIC, GoodEvil.GOOD),
            "ln": (LawChaos.LAWFUL, GoodEvil.NEUTRAL),
            "tn": (LawChaos.NEUTRAL, GoodEvil.NEUTRAL),
            "n": (LawChaos.NEUTRAL, GoodEvil.NEUTRAL),  # Just "N" = True Neutral
            "cn": (LawChaos.CHAOTIC, GoodEvil.NEUTRAL),
            "le": (LawChaos.LAWFUL, GoodEvil.EVIL),
            "ne": (LawChaos.NEUTRAL, GoodEvil.EVIL),
            "ce": (LawChaos.CHAOTIC, GoodEvil.EVIL),
        }
        
        if s in code_map:
            lc, ge = code_map[s]
            return cls(lc, ge)
        
        # Handle full names
        if "true neutral" in s or s == "neutral":
            return cls(LawChaos.NEUTRAL, GoodEvil.NEUTRAL)
        
        # Parse "lawful good", "chaotic evil", etc.
        parts = s.split()
        if len(parts) != 2:
            raise ValueError(f"Cannot parse alignment: '{s}'")
        
        law_chaos_str, good_evil_str = parts
        
        try:
            law_chaos = LawChaos(law_chaos_str)
            good_evil = GoodEvil(good_evil_str)
        except ValueError:
            raise ValueError(f"Cannot parse alignment: '{s}'")
        
        return cls(law_chaos, good_evil)
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return f"Alignment({self.law_chaos}, {self.good_evil})"

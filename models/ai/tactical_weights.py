# models/ai/tactical_weights.py
"""
Tactical behavior weights for AI decision-making.

These weights influence how an AI-controlled entity makes combat decisions.
They can be derived from alignment or customized directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class TacticalWeights:
    """
    Numerical weights that drive AI tactical decisions.
    
    All values are floats from 0.0 to 1.0, where:
    - 0.0 = never/minimum
    - 0.5 = neutral/balanced
    - 1.0 = always/maximum
    
    These weights are used by the AI prompt builder to describe behavioral
    tendencies, and can also be used by deterministic fallback logic.
    """
    
    # Group tactics vs solo plays
    # 0 = lone wolf, 1 = always coordinates
    coordination: float = 0.5
    
    # Optimal moves vs surprising moves
    # 0 = unpredictable/random, 1 = always optimal play
    predictability: float = 0.5
    
    # Shield others vs ignore them
    # 0 = ignores allies completely, 1 = will die to protect allies
    ally_protection: float = 0.5
    
    # Spare fallen foes vs finish them
    # 0 = executes downed enemies, 1 = always spares
    mercy: float = 0.5
    
    # Take hits for others vs preserve self
    # 0 = pure self-preservation, 1 = gladly sacrifices self
    self_sacrifice: float = 0.5
    
    # Easy kills vs threats first
    # 0 = targets weakest enemies, 1 = targets biggest threats
    target_priority: float = 0.5
    
    # Fair fight vs dirty tricks
    # 0 = uses every dirty trick, 1 = fights with honor
    honor: float = 0.5
    
    # Defensive vs offensive posture
    # 0 = very defensive, 1 = hyper-aggressive
    aggression: float = 0.5
    
    # HP percentage at which to consider fleeing
    # 0 = never flees, 1 = flees at first scratch
    flee_threshold: float = 0.3
    
    def __post_init__(self):
        """Validate all weights are in [0, 1]."""
        for name, value in asdict(self).items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0.0 and 1.0, got {value}")
    
    # -------------------------------------------------------------------------
    # Behavioral Interpretation
    # -------------------------------------------------------------------------
    
    @property
    def is_aggressive(self) -> bool:
        """True if aggression > 0.6."""
        return self.aggression > 0.6
    
    @property
    def is_defensive(self) -> bool:
        """True if aggression < 0.4."""
        return self.aggression < 0.4
    
    @property
    def is_protective(self) -> bool:
        """True if ally_protection > 0.7."""
        return self.ally_protection > 0.7
    
    @property
    def is_selfish(self) -> bool:
        """True if self_sacrifice < 0.3 and ally_protection < 0.3."""
        return self.self_sacrifice < 0.3 and self.ally_protection < 0.3
    
    @property
    def is_honorable(self) -> bool:
        """True if honor > 0.6 and mercy > 0.5."""
        return self.honor > 0.6 and self.mercy > 0.5
    
    @property
    def is_ruthless(self) -> bool:
        """True if mercy < 0.3."""
        return self.mercy < 0.3
    
    @property
    def is_cowardly(self) -> bool:
        """True if flee_threshold > 0.5."""
        return self.flee_threshold > 0.5
    
    @property
    def is_unpredictable(self) -> bool:
        """True if predictability < 0.3."""
        return self.predictability < 0.3
    
    @property
    def is_team_player(self) -> bool:
        """True if coordination > 0.7."""
        return self.coordination > 0.7
    
    # -------------------------------------------------------------------------
    # Behavioral Descriptions (for prompts)
    # -------------------------------------------------------------------------
    
    def describe_aggression(self) -> str:
        """Return a natural language description of aggression level."""
        if self.aggression >= 0.8:
            return "extremely aggressive, always on the offensive"
        elif self.aggression >= 0.6:
            return "aggressive, prefers offensive action"
        elif self.aggression >= 0.4:
            return "balanced between offense and defense"
        elif self.aggression >= 0.2:
            return "cautious, prefers defensive positioning"
        else:
            return "very defensive, avoids direct confrontation"
    
    def describe_loyalty(self) -> str:
        """Return a natural language description of ally loyalty."""
        if self.ally_protection >= 0.8:
            return "fiercely protective of allies, will die for them"
        elif self.ally_protection >= 0.6:
            return "protective of allies, prioritizes their safety"
        elif self.ally_protection >= 0.4:
            return "considers allies but won't sacrifice much for them"
        elif self.ally_protection >= 0.2:
            return "mostly self-interested, allies are secondary"
        else:
            return "cares nothing for allies, purely self-focused"
    
    def describe_mercy(self) -> str:
        """Return a natural language description of mercy level."""
        if self.mercy >= 0.8:
            return "merciful, always spares fallen foes"
        elif self.mercy >= 0.6:
            return "generally merciful, prefers to spare enemies"
        elif self.mercy >= 0.4:
            return "pragmatic about mercy, depends on situation"
        elif self.mercy >= 0.2:
            return "rarely shows mercy, finishes most enemies"
        else:
            return "ruthless, never spares a fallen foe"
    
    def describe_flee_behavior(self) -> str:
        """Return a natural language description of flee threshold."""
        if self.flee_threshold >= 0.7:
            return "cowardly, will flee at first sign of danger"
        elif self.flee_threshold >= 0.5:
            return "cautious, will retreat when wounded"
        elif self.flee_threshold >= 0.3:
            return "steady, retreats only when badly hurt"
        elif self.flee_threshold >= 0.15:
            return "stubborn, fights until near death"
        else:
            return "fearless, never retreats"
    
    def get_behavioral_summary(self) -> list[str]:
        """
        Return a list of behavioral trait strings for prompt inclusion.
        
        Only includes notable traits (not middle-of-the-road values).
        """
        traits = []
        
        if self.aggression >= 0.7:
            traits.append("highly aggressive")
        elif self.aggression <= 0.3:
            traits.append("defensive-minded")
        
        if self.ally_protection >= 0.7:
            traits.append("protective of allies")
        elif self.ally_protection <= 0.3:
            traits.append("self-interested")
        
        if self.coordination >= 0.7:
            traits.append("coordinates with allies")
        elif self.coordination <= 0.3:
            traits.append("acts independently")
        
        if self.predictability <= 0.3:
            traits.append("unpredictable")
        
        if self.mercy <= 0.2:
            traits.append("ruthless")
        elif self.mercy >= 0.8:
            traits.append("merciful")
        
        if self.honor >= 0.7:
            traits.append("fights with honor")
        elif self.honor <= 0.3:
            traits.append("uses dirty tricks")
        
        if self.self_sacrifice >= 0.7:
            traits.append("willing to sacrifice self for others")
        
        if self.flee_threshold >= 0.6:
            traits.append("cowardly")
        elif self.flee_threshold <= 0.15:
            traits.append("fearless")
        
        if self.target_priority >= 0.7:
            traits.append("focuses on biggest threats")
        elif self.target_priority <= 0.3:
            traits.append("picks off weak targets")
        
        return traits
    
    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------
    
    def to_dict(self) -> dict[str, float]:
        """Serialize to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TacticalWeights:
        """Deserialize from dictionary."""
        return cls(**{k: float(v) for k, v in data.items()})
    
    # -------------------------------------------------------------------------
    # Presets
    # -------------------------------------------------------------------------
    
    @classmethod
    def cowardly_minion(cls) -> TacticalWeights:
        """Preset: Goblin grunt, kobold, etc."""
        return cls(
            coordination=0.4,
            predictability=0.5,
            ally_protection=0.2,
            mercy=0.3,
            self_sacrifice=0.1,
            target_priority=0.3,
            honor=0.3,
            aggression=0.3,
            flee_threshold=0.6,
        )
    
    @classmethod
    def fanatical_cultist(cls) -> TacticalWeights:
        """Preset: Cultist, zealot, true believer."""
        return cls(
            coordination=0.7,
            predictability=0.6,
            ally_protection=0.5,
            mercy=0.1,
            self_sacrifice=0.9,
            target_priority=0.5,
            honor=0.4,
            aggression=0.8,
            flee_threshold=0.05,
        )
    
    @classmethod
    def cunning_assassin(cls) -> TacticalWeights:
        """Preset: Assassin, rogue, ambush predator."""
        return cls(
            coordination=0.3,
            predictability=0.4,
            ally_protection=0.2,
            mercy=0.2,
            self_sacrifice=0.1,
            target_priority=0.2,  # Targets weak/isolated
            honor=0.1,
            aggression=0.5,
            flee_threshold=0.4,
        )
    
    @classmethod
    def protective_guardian(cls) -> TacticalWeights:
        """Preset: Paladin, bodyguard, loyal defender."""
        return cls(
            coordination=0.8,
            predictability=0.7,
            ally_protection=0.9,
            mercy=0.7,
            self_sacrifice=0.8,
            target_priority=0.8,  # Threats to allies first
            honor=0.8,
            aggression=0.4,
            flee_threshold=0.1,
        )
    
    @classmethod
    def berserker(cls) -> TacticalWeights:
        """Preset: Barbarian, orc, rage-driven."""
        return cls(
            coordination=0.2,
            predictability=0.3,
            ally_protection=0.3,
            mercy=0.1,
            self_sacrifice=0.4,
            target_priority=0.7,  # Strongest enemy
            honor=0.5,
            aggression=0.95,
            flee_threshold=0.05,
        )
    
    @classmethod
    def cold_tactician(cls) -> TacticalWeights:
        """Preset: Optimal play, no emotions."""
        return cls(
            coordination=0.7,
            predictability=0.9,
            ally_protection=0.5,
            mercy=0.3,
            self_sacrifice=0.3,
            target_priority=0.6,
            honor=0.4,
            aggression=0.5,
            flee_threshold=0.3,
        )

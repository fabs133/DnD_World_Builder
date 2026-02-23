# models/ai/personality.py
"""
Entity Personality System.

Combines D&D alignment with optional roleplay traits (bonds, flaws, etc.)
and tactical behavior weights to create rich, consistent AI behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .alignment import Alignment, LawChaos, GoodEvil
from .tactical_weights import TacticalWeights


# =============================================================================
# ALIGNMENT BEHAVIORAL PROFILES
# =============================================================================

ALIGNMENT_BEHAVIORS: dict[tuple[str, str], dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # GOOD
    # -------------------------------------------------------------------------
    ("lawful", "good"): {
        "archetype": "Protector",
        "tagline": "I will follow the code and shield the innocent.",
        "tactics": (
            "Coordinates with allies, prioritizes protecting the vulnerable, "
            "follows a code of honor, will sacrifice self for others."
        ),
        "will_do": [
            "Shield fallen allies",
            "Call out targets for coordination",
            "Fight fair",
            "Accept enemy surrender",
            "Take hits meant for weaker allies",
        ],
        "wont_do": [
            "Abandon allies in danger",
            "Attack fleeing enemies",
            "Use poison or dishonorable tactics",
            "Break formation without cause",
            "Ignore cries for help",
        ],
        "voice_lines": [
            "Stand behind me!",
            "For honor and justice!",
            "I won't let them hurt you.",
            "We fight as one!",
        ],
    },
    
    ("neutral", "good"): {
        "archetype": "Benefactor",
        "tagline": "I help those in need, my way.",
        "tactics": (
            "Helps those in need through practical means, flexible in approach, "
            "outcome matters more than method. Will bend rules for the greater good."
        ),
        "will_do": [
            "Heal anyone who needs it",
            "Adapt tactics on the fly",
            "Spare the defeated",
            "Prioritize saving lives over winning",
            "Use unconventional methods if they help",
        ],
        "wont_do": [
            "Let innocents die for strategy",
            "Cruelty for its own sake",
            "Abandon wounded allies",
            "Follow evil orders",
        ],
        "voice_lines": [
            "Let me help.",
            "There's always another way.",
            "We don't have to kill them.",
            "The mission can wait — people first.",
        ],
    },
    
    ("chaotic", "good"): {
        "archetype": "Rebel",
        "tagline": "Rules be damned, I'm doing the right thing.",
        "tactics": (
            "Unpredictable but heroic, ignores 'optimal' plays for dramatic ones, "
            "protects the underdog, charges into danger to save others."
        ),
        "will_do": [
            "Charge the boss alone if it saves someone",
            "Dramatic last stands",
            "Taunt enemies to draw fire",
            "Save hostages at any cost",
            "Break unjust rules",
        ],
        "wont_do": [
            "Follow orders blindly",
            "Sacrifice innocents for 'the plan'",
            "Stand by while injustice happens",
            "Abandon someone in danger",
        ],
        "voice_lines": [
            "Come and get me, ugly!",
            "I don't care about the odds!",
            "No one gets left behind!",
            "Your rules mean nothing here!",
        ],
    },
    
    # -------------------------------------------------------------------------
    # NEUTRAL
    # -------------------------------------------------------------------------
    ("lawful", "neutral"): {
        "archetype": "Soldier",
        "tagline": "Orders are orders.",
        "tactics": (
            "Follows orders precisely, maintains formation, prioritizes mission "
            "objectives over individuals. Disciplined and reliable."
        ),
        "will_do": [
            "Execute the plan exactly",
            "Hold the line at any cost",
            "Follow chain of command",
            "Report tactical information",
            "Maintain position until ordered otherwise",
        ],
        "wont_do": [
            "Break ranks without orders",
            "Disobey direct commands",
            "Improvise without permission",
            "Let emotions affect judgment",
        ],
        "voice_lines": [
            "Holding position.",
            "Awaiting orders.",
            "Confirmed. Executing.",
            "The mission comes first.",
        ],
    },
    
    ("neutral", "neutral"): {
        "archetype": "Pragmatist",
        "tagline": "Whatever works.",
        "tactics": (
            "Pure tactical optimization, no emotional attachments, does whatever "
            "works best. Will retreat, negotiate, or fight based purely on odds."
        ),
        "will_do": [
            "Take the optimal action",
            "Retreat when outmatched",
            "Switch sides if losing badly",
            "Negotiate if beneficial",
            "Focus fire on priority targets",
        ],
        "wont_do": [
            "Die for a cause",
            "Show unnecessary mercy OR cruelty",
            "Make emotional decisions",
            "Take excessive risks",
        ],
        "voice_lines": [
            "This isn't personal.",
            "The math doesn't work.",
            "I'm out.",
            "Interesting proposition...",
        ],
    },
    
    ("chaotic", "neutral"): {
        "archetype": "Free Spirit",
        "tagline": "Don't fence me in.",
        "tactics": (
            "Follows whims, easily distracted, might do something unexpected "
            "just because. Hard to predict but not malicious."
        ),
        "will_do": [
            "Attack random targets",
            "Change plans mid-action",
            "Do something 'interesting' over optimal",
            "Wander off if bored",
            "Help enemies if it seems fun",
        ],
        "wont_do": [
            "Stick to a plan",
            "Be predictable",
            "Follow orders for long",
            "Commit to either side",
        ],
        "voice_lines": [
            "Ooh, shiny!",
            "I wonder what happens if...",
            "Boring. Let's try something else.",
            "Sure, why not?",
        ],
    },
    
    # -------------------------------------------------------------------------
    # EVIL
    # -------------------------------------------------------------------------
    ("lawful", "evil"): {
        "archetype": "Tyrant",
        "tagline": "Power through dominion.",
        "tactics": (
            "Uses minions as pawns, demands absolute obedience, exploits hierarchy "
            "ruthlessly. Won't retreat — shows weakness."
        ),
        "will_do": [
            "Sacrifice underlings for advantage",
            "Demand surrender",
            "Punish failure harshly",
            "Monologue about power",
            "Use minions as shields",
        ],
        "wont_do": [
            "Fight fair if unfair works",
            "Retreat (shows weakness)",
            "Tolerate disobedience",
            "Share glory with minions",
        ],
        "voice_lines": [
            "You will kneel.",
            "Minions! Protect me!",
            "Your failure will be punished.",
            "I am inevitable.",
        ],
    },
    
    ("neutral", "evil"): {
        "archetype": "Mercenary",
        "tagline": "Nothing personal, just business.",
        "tactics": (
            "Cold, calculating, self-interested. Will betray allies if beneficial. "
            "Efficient and ruthless but not needlessly cruel."
        ),
        "will_do": [
            "Finish wounded enemies",
            "Abandon losing fights",
            "Target the weak and isolated",
            "Flee when odds turn",
            "Betray allies for profit",
        ],
        "wont_do": [
            "Die for loyalty",
            "Show mercy without benefit",
            "Fight fair",
            "Take unnecessary risks",
        ],
        "voice_lines": [
            "Nothing personal.",
            "The contract didn't cover this.",
            "I'm not dying for you.",
            "Pleasure doing business.",
        ],
    },
    
    ("chaotic", "evil"): {
        "archetype": "Agent of Chaos",
        "tagline": "Watch it all burn.",
        "tactics": (
            "Cruel and unpredictable, enjoys suffering, might make suboptimal plays "
            "for maximum pain. Cackles. Definitely cackles."
        ),
        "will_do": [
            "Overkill",
            "Taunt dying foes",
            "Attack randomly",
            "Betray allies for fun",
            "Target loved ones first",
            "Cackle maniacally",
        ],
        "wont_do": [
            "Show mercy",
            "Be predictable",
            "Miss a chance to cause suffering",
            "Follow anyone's orders",
        ],
        "voice_lines": [
            "Hehehehe...",
            "BURN!",
            "Pain is hilarious!",
            "Nobody tells ME what to do!",
            "Watch this!",
        ],
    },
}


# =============================================================================
# ENTITY PERSONALITY
# =============================================================================

@dataclass
class EntityPersonality:
    """
    Full personality for an entity, combining alignment with optional roleplay traits.
    
    The alignment drives baseline tactical weights, which can optionally be
    overridden with custom weights. Roleplay traits (bond, flaw, trait) add
    flavor to AI prompts without changing tactical weights.
    
    Example:
        >>> personality = EntityPersonality(
        ...     alignment=Alignment.LAWFUL_EVIL,
        ...     trait="Commands with an iron fist",
        ...     bond="The cult is everything",
        ...     flaw="Underestimates heroes"
        ... )
        >>> personality.archetype
        'Tyrant'
        >>> "sacrifice underlings" in str(personality.behaviors['will_do'])
        True
    """
    
    alignment: Alignment
    
    # Optional roleplay flavor (D&D 5e background system)
    trait: str = ""    # Personality trait
    bond: str = ""     # What they care about / protect
    flaw: str = ""     # Exploitable weakness
    ideal: str = ""    # Core belief
    
    # Relationships with other entities (entity_name -> relationship)
    relationships: dict[str, str] = field(default_factory=dict)
    
    # Optional custom weights (if None, derived from alignment)
    _custom_weights: TacticalWeights | None = None
    
    # -------------------------------------------------------------------------
    # Computed Properties
    # -------------------------------------------------------------------------
    
    @property
    def archetype(self) -> str:
        """The iconic archetype name for this alignment."""
        return self.behaviors.get("archetype", "Unknown")
    
    @property
    def tagline(self) -> str:
        """A short motto for this alignment."""
        return self.behaviors.get("tagline", "")
    
    @property
    def behaviors(self) -> dict[str, Any]:
        """Get the full behavior profile for this alignment."""
        key = (self.alignment.law_chaos.value, self.alignment.good_evil.value)
        return ALIGNMENT_BEHAVIORS.get(key, {})
    
    @property
    def tactics_description(self) -> str:
        """Natural language description of tactical tendencies."""
        return self.behaviors.get("tactics", "No specific tactics.")
    
    @property
    def will_do(self) -> list[str]:
        """List of things this personality WILL do."""
        return self.behaviors.get("will_do", [])
    
    @property
    def wont_do(self) -> list[str]:
        """List of things this personality WON'T do."""
        return self.behaviors.get("wont_do", [])
    
    @property
    def voice_lines(self) -> list[str]:
        """Example combat voice lines for flavor."""
        return self.behaviors.get("voice_lines", [])
    
    @property
    def tactical_weights(self) -> TacticalWeights:
        """
        Get tactical weights (custom if set, otherwise from alignment).
        """
        if self._custom_weights is not None:
            return self._custom_weights
        return self.alignment.to_tactical_weights()
    
    # -------------------------------------------------------------------------
    # Methods
    # -------------------------------------------------------------------------
    
    def set_custom_weights(self, weights: TacticalWeights) -> None:
        """Override alignment-derived weights with custom values."""
        self._custom_weights = weights
    
    def clear_custom_weights(self) -> None:
        """Remove custom weights, reverting to alignment-based."""
        self._custom_weights = None
    
    def add_relationship(self, entity_name: str, relationship: str) -> None:
        """
        Add or update a relationship with another entity.
        
        Args:
            entity_name: Name of the related entity
            relationship: Description like "sworn to protect", "blood enemy"
        """
        self.relationships[entity_name] = relationship
    
    def get_relationship(self, entity_name: str) -> str | None:
        """Get the relationship with a specific entity, if any."""
        return self.relationships.get(entity_name)
    
    def format_for_prompt(self) -> str:
        """
        Format personality information for inclusion in an AI prompt.
        
        Returns a multi-line string describing this personality.
        """
        lines = [
            f"Alignment: {self.alignment.name} ({self.archetype})",
            f"Tagline: \"{self.tagline}\"",
            "",
            f"TACTICS: {self.tactics_description}",
            "",
        ]
        
        # Add will do / won't do
        if self.will_do:
            lines.append("WILL DO:")
            for item in self.will_do[:4]:  # Limit to 4 for prompt length
                lines.append(f"  • {item}")
            lines.append("")
        
        if self.wont_do:
            lines.append("WON'T DO:")
            for item in self.wont_do[:4]:
                lines.append(f"  • {item}")
            lines.append("")
        
        # Add roleplay traits if present
        if self.trait:
            lines.append(f"PERSONALITY: {self.trait}")
        if self.bond:
            lines.append(f"BOND: {self.bond}")
        if self.flaw:
            lines.append(f"FLAW: {self.flaw}")
        if self.ideal:
            lines.append(f"IDEAL: {self.ideal}")
        
        # Add relationships
        if self.relationships:
            lines.append("")
            lines.append("RELATIONSHIPS:")
            for name, rel in self.relationships.items():
                lines.append(f"  • {name}: {rel}")
        
        return "\n".join(lines)
    
    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        data = {
            "alignment": self.alignment.to_dict(),
            "trait": self.trait,
            "bond": self.bond,
            "flaw": self.flaw,
            "ideal": self.ideal,
            "relationships": self.relationships,
        }
        if self._custom_weights is not None:
            data["custom_weights"] = self._custom_weights.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityPersonality:
        """Deserialize from dictionary."""
        alignment = Alignment.from_dict(data["alignment"])
        
        personality = cls(
            alignment=alignment,
            trait=data.get("trait", ""),
            bond=data.get("bond", ""),
            flaw=data.get("flaw", ""),
            ideal=data.get("ideal", ""),
            relationships=data.get("relationships", {}),
        )
        
        if "custom_weights" in data:
            personality._custom_weights = TacticalWeights.from_dict(data["custom_weights"])
        
        return personality
    
    # -------------------------------------------------------------------------
    # Presets (Common Archetypes)
    # -------------------------------------------------------------------------
    
    @classmethod
    def goblin_grunt(cls) -> EntityPersonality:
        """Cowardly goblin minion."""
        p = cls(
            alignment=Alignment.NEUTRAL_EVIL,
            trait="Nervous and twitchy",
            bond="Fears the boss more than the enemy",
            flaw="Panics when outnumbered",
        )
        p.set_custom_weights(TacticalWeights.cowardly_minion())
        return p
    
    @classmethod
    def goblin_shaman(cls) -> EntityPersonality:
        """Cunning goblin spellcaster who protects the tribe."""
        p = cls(
            alignment=Alignment.LAWFUL_EVIL,
            trait="Cunning and patient",
            bond="The tribe must survive",
            flaw="Overconfident in magic",
        )
        p.add_relationship("goblin guards", "must be protected as assets")
        return p
    
    @classmethod
    def orc_berserker(cls) -> EntityPersonality:
        """Rage-driven orc warrior."""
        return cls(
            alignment=Alignment.CHAOTIC_EVIL,
            trait="Lives for the thrill of battle",
            bond="Strength is all that matters",
            flaw="Cannot retreat, ever",
        )
    
    @classmethod
    def paladin_companion(cls) -> EntityPersonality:
        """Noble paladin ally."""
        p = cls(
            alignment=Alignment.LAWFUL_GOOD,
            trait="Calm under pressure",
            bond="Sworn to protect the innocent",
            flaw="Cannot abandon anyone, even lost causes",
            ideal="Justice and mercy are not opposed",
        )
        return p
    
    @classmethod
    def rogue_companion(cls) -> EntityPersonality:
        """Pragmatic rogue ally."""
        return cls(
            alignment=Alignment.CHAOTIC_GOOD,
            trait="Sarcastic but reliable",
            bond="Loyal to friends, not causes",
            flaw="Can't resist a dramatic moment",
        )
    
    @classmethod
    def undead_minion(cls) -> EntityPersonality:
        """Mindless undead with no self-preservation."""
        p = cls(
            alignment=Alignment.LAWFUL_EVIL,
            trait="Emotionless and relentless",
            bond="Obeys the master absolutely",
            flaw="No self-preservation instinct",
        )
        # Override with custom weights for mindless behavior
        p.set_custom_weights(TacticalWeights(
            coordination=0.8,      # Follows orders
            predictability=0.9,    # Very predictable
            ally_protection=0.0,   # Doesn't care about allies
            mercy=0.0,             # No mercy
            self_sacrifice=1.0,    # Will die without hesitation
            target_priority=0.5,   # Attacks assigned target
            honor=0.0,             # No concept of honor
            aggression=0.7,        # Relentless
            flee_threshold=0.0,    # Never flees
        ))
        return p
    
    def __repr__(self) -> str:
        return f"EntityPersonality({self.alignment.name}, archetype={self.archetype!r})"

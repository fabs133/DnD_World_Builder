"""
Rule Registry - Catalog of All Available Specifications

This module provides:
- Centralized registry of all rule specifications
- Categorization (base rules, optional rules, custom rules)
- Rich metadata for UI display
- Serialization for storage

Design:
- RuleDefinition: Metadata wrapper around a Specification
- RuleCategory: Grouping for UI organization  
- RuleRegistry: Central catalog with query/filter capabilities
- BASE_RULES: Core D&D 5e rules that should always be available
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Type
from enum import Enum
import json

from domain.specs.base import Specification, SpecResult


class RuleCategory(Enum):
    """Categories for organizing rules in the UI."""
    
    # Core rules - typically always active
    MOVEMENT = "movement"
    COMBAT = "combat"
    SPELLCASTING = "spellcasting"
    CONDITIONS = "conditions"
    RESOURCES = "resources"
    
    # Trigger/event rules
    TRAPS = "traps"
    ENVIRONMENTAL = "environmental"
    SOCIAL = "social"
    
    # Meta categories
    BASE = "base"           # Core rules that should always apply
    OPTIONAL = "optional"   # Standard D&D rules that can be toggled
    VARIANT = "variant"     # Variant/homebrew rules
    CUSTOM = "custom"       # User-created rules


class RuleScope(Enum):
    """What a rule evaluates against."""
    ENTITY = "entity"       # Evaluates an entity (player, NPC, enemy)
    TILE = "tile"           # Evaluates a tile
    SCENARIO = "scenario"   # Evaluates global scenario state
    INTERACTION = "interaction"  # Evaluates entity + target


@dataclass
class RuleParameter:
    """
    Definition of a configurable parameter for a rule.
    
    This is the "mask" - it defines what inputs a rule needs,
    allowing the UI to generate appropriate input fields.
    """
    name: str
    param_type: str  # "int", "float", "str", "skill", "ability", "condition", "entity_type"
    label: str
    description: str = ""
    default: Any = None
    required: bool = True
    
    # Constraints for validation
    min_value: int | float | None = None
    max_value: int | float | None = None
    choices: list[str] | None = None  # For enum-like parameters
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "param_type": self.param_type,
            "label": self.label,
            "description": self.description,
            "default": self.default,
            "required": self.required,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "choices": self.choices,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuleParameter:
        return cls(**data)


@dataclass
class RuleDefinition:
    """
    Metadata wrapper around a Specification.
    
    This is what gets displayed in the rule editor UI.
    It contains everything needed to:
    - Display the rule in a list/tree
    - Show configuration options
    - Instantiate the spec with custom parameters
    """
    rule_id: str
    name: str
    description: str
    category: RuleCategory
    scope: RuleScope
    
    # The spec class or factory function
    spec_class: Type[Specification] | Callable[..., Specification]
    
    # Parameters that can be configured
    parameters: list[RuleParameter] = field(default_factory=list)
    
    # UI metadata
    icon: str = "📜"  # Emoji or icon name
    tags: list[str] = field(default_factory=list)
    
    # Rule behavior
    is_base_rule: bool = False      # Always available, can't be removed
    is_invertible: bool = True      # Can apply as NOT(rule)
    default_enabled: bool = True    # Enabled by default in new scenarios
    
    # Documentation
    examples: list[str] = field(default_factory=list)
    see_also: list[str] = field(default_factory=list)  # Related rule IDs
    
    def create_spec(self, **kwargs) -> Specification:
        """
        Instantiate the specification with given parameters.
        
        Args:
            **kwargs: Parameter values matching self.parameters
        
        Returns:
            Configured Specification instance
        """
        # Apply defaults for missing parameters
        for param in self.parameters:
            if param.name not in kwargs and param.default is not None:
                kwargs[param.name] = param.default
        
        # Validate required parameters
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                raise ValueError(f"Missing required parameter: {param.name}")
        
        return self.spec_class(**kwargs)
    
    def validate_params(self, **kwargs) -> list[str]:
        """
        Validate parameters against constraints.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        for param in self.parameters:
            if param.name not in kwargs:
                if param.required:
                    errors.append(f"Missing required parameter: {param.label}")
                continue
            
            value = kwargs[param.name]
            
            # Type checking
            if param.param_type == "int" and not isinstance(value, int):
                errors.append(f"{param.label} must be an integer")
            elif param.param_type == "float" and not isinstance(value, (int, float)):
                errors.append(f"{param.label} must be a number")
            elif param.param_type == "str" and not isinstance(value, str):
                errors.append(f"{param.label} must be text")
            
            # Range checking
            if param.min_value is not None and value < param.min_value:
                errors.append(f"{param.label} must be at least {param.min_value}")
            if param.max_value is not None and value > param.max_value:
                errors.append(f"{param.label} must be at most {param.max_value}")
            
            # Choice checking
            if param.choices is not None and value not in param.choices:
                errors.append(f"{param.label} must be one of: {', '.join(param.choices)}")
        
        return errors
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize for storage (without spec_class)."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "scope": self.scope.value,
            "parameters": [p.to_dict() for p in self.parameters],
            "icon": self.icon,
            "tags": self.tags,
            "is_base_rule": self.is_base_rule,
            "is_invertible": self.is_invertible,
            "default_enabled": self.default_enabled,
            "examples": self.examples,
            "see_also": self.see_also,
        }


class RuleRegistry:
    """
    Central catalog of all available rules.
    
    This is the source of truth for what rules exist and how to use them.
    The UI queries this to build the rule browser/editor.
    
    Usage:
        registry = RuleRegistry()
        registry.register_defaults()  # Load base D&D rules
        
        # Query rules
        combat_rules = registry.get_by_category(RuleCategory.COMBAT)
        skill_checks = registry.search("skill check")
        
        # Create configured spec
        rule_def = registry.get("skill_check")
        spec = rule_def.create_spec(skill="Perception", dc=15)
    """
    
    def __init__(self):
        self._rules: dict[str, RuleDefinition] = {}
        self._by_category: dict[RuleCategory, list[str]] = {cat: [] for cat in RuleCategory}
    
    def register(self, rule: RuleDefinition):
        """Register a rule definition."""
        self._rules[rule.rule_id] = rule
        self._by_category[rule.category].append(rule.rule_id)
    
    def unregister(self, rule_id: str):
        """Remove a rule definition."""
        if rule_id in self._rules:
            rule = self._rules.pop(rule_id)
            self._by_category[rule.category].remove(rule_id)
    
    def get(self, rule_id: str) -> RuleDefinition | None:
        """Get a rule by ID."""
        return self._rules.get(rule_id)
    
    def get_all(self) -> list[RuleDefinition]:
        """Get all registered rules."""
        return list(self._rules.values())
    
    def get_by_category(self, category: RuleCategory) -> list[RuleDefinition]:
        """Get all rules in a category."""
        return [self._rules[rid] for rid in self._by_category.get(category, [])]
    
    def get_base_rules(self) -> list[RuleDefinition]:
        """Get all base rules (always active)."""
        return [r for r in self._rules.values() if r.is_base_rule]
    
    def get_optional_rules(self) -> list[RuleDefinition]:
        """Get all optional rules (can be toggled)."""
        return [r for r in self._rules.values() if not r.is_base_rule]
    
    def search(self, query: str) -> list[RuleDefinition]:
        """Search rules by name, description, or tags."""
        query = query.lower()
        results = []
        
        for rule in self._rules.values():
            if (query in rule.name.lower() or 
                query in rule.description.lower() or
                any(query in tag.lower() for tag in rule.tags)):
                results.append(rule)
        
        return results
    
    def get_by_scope(self, scope: RuleScope) -> list[RuleDefinition]:
        """Get all rules that evaluate a specific scope."""
        return [r for r in self._rules.values() if r.scope == scope]
    
    def register_defaults(self):
        """Register all default D&D 5e rules."""
        _register_base_rules(self)
        _register_combat_rules(self)
        _register_movement_rules(self)
        _register_condition_rules(self)
        _register_trigger_rules(self)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize registry (for export)."""
        return {
            "rules": {rid: r.to_dict() for rid, r in self._rules.items()}
        }
    
    def export_json(self, path: str):
        """Export registry to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# Default Rule Definitions
# ─────────────────────────────────────────────────────────────────────────────

# Common parameter definitions (reusable)
PARAM_SKILL = RuleParameter(
    name="skill",
    param_type="skill",
    label="Skill",
    description="The skill to check",
    choices=[
        "Acrobatics", "Animal Handling", "Arcana", "Athletics",
        "Deception", "History", "Insight", "Intimidation",
        "Investigation", "Medicine", "Nature", "Perception",
        "Performance", "Persuasion", "Religion", "Sleight of Hand",
        "Stealth", "Survival"
    ]
)

PARAM_ABILITY = RuleParameter(
    name="ability",
    param_type="ability",
    label="Ability",
    description="The ability score to use",
    choices=["STR", "DEX", "CON", "INT", "WIS", "CHA"]
)

PARAM_DC = RuleParameter(
    name="dc",
    param_type="int",
    label="Difficulty Class (DC)",
    description="The target number to meet or exceed",
    default=10,
    min_value=1,
    max_value=30
)

PARAM_DISTANCE = RuleParameter(
    name="required",
    param_type="int",
    label="Distance (feet)",
    description="Distance in feet",
    default=5,
    min_value=0,
    max_value=1000
)

PARAM_RANGE = RuleParameter(
    name="max_range",
    param_type="int",
    label="Maximum Range (feet)",
    description="Maximum range in feet",
    default=30,
    min_value=5,
    max_value=1000
)


def _register_base_rules(registry: RuleRegistry):
    """Register core rules that are always available."""
    from domain.specs.checks import SkillCheckSpec, SavingThrowSpec
    from domain.specs.entity import IsAlive, CanTakeAction
    
    registry.register(RuleDefinition(
        rule_id="is_alive",
        name="Is Alive",
        description="Entity has HP > 0 and is not dead",
        category=RuleCategory.BASE,
        scope=RuleScope.ENTITY,
        spec_class=IsAlive,
        parameters=[],
        icon="❤️",
        tags=["hp", "death", "basic"],
        is_base_rule=True,
        examples=["Check if a creature can be targeted by most effects"],
    ))
    
    registry.register(RuleDefinition(
        rule_id="can_take_action",
        name="Can Take Action",
        description="Entity is not incapacitated and has not used their action",
        category=RuleCategory.BASE,
        scope=RuleScope.ENTITY,
        spec_class=CanTakeAction,
        parameters=[],
        icon="⚔️",
        tags=["action", "turn", "basic"],
        is_base_rule=True,
        examples=["Prerequisite for Attack, Cast Spell, Dash, etc."],
    ))


def _register_combat_rules(registry: RuleRegistry):
    """Register combat-related rules."""
    from domain.specs.checks import SkillCheckSpec, SavingThrowSpec
    from domain.specs.movement import InRange, IsAdjacent
    from domain.specs.entity import IsIncapacitated, HasCondition, CanTakeReaction
    
    registry.register(RuleDefinition(
        rule_id="skill_check",
        name="Skill Check",
        description="Roll d20 + skill modifier against a DC",
        category=RuleCategory.COMBAT,
        scope=RuleScope.ENTITY,
        spec_class=SkillCheckSpec,
        parameters=[PARAM_SKILL, PARAM_DC],
        icon="🎲",
        tags=["skill", "roll", "d20"],
        is_base_rule=False,
        is_invertible=True,
        examples=[
            "Perception DC 15 to spot a hidden enemy",
            "Stealth DC 12 to sneak past guards",
        ],
    ))
    
    registry.register(RuleDefinition(
        rule_id="saving_throw",
        name="Saving Throw",
        description="Roll d20 + save modifier against a DC",
        category=RuleCategory.COMBAT,
        scope=RuleScope.ENTITY,
        spec_class=SavingThrowSpec,
        parameters=[PARAM_ABILITY, PARAM_DC],
        icon="🛡️",
        tags=["save", "roll", "d20"],
        is_base_rule=False,
        examples=[
            "DEX save DC 14 to avoid fireball damage",
            "WIS save DC 13 to resist charm",
        ],
    ))
    
    registry.register(RuleDefinition(
        rule_id="in_range",
        name="In Range",
        description="Target is within specified distance",
        category=RuleCategory.COMBAT,
        scope=RuleScope.INTERACTION,
        spec_class=InRange,
        parameters=[
            PARAM_RANGE,
            RuleParameter(
                name="min_range",
                param_type="int",
                label="Minimum Range (feet)",
                description="Minimum range (for thrown weapons, etc.)",
                default=0,
                min_value=0,
            ),
        ],
        icon="📏",
        tags=["range", "distance", "targeting"],
        is_base_rule=False,
        examples=[
            "Melee attack range (5 ft)",
            "Shortbow range (80 ft)",
        ],
    ))
    
    registry.register(RuleDefinition(
        rule_id="is_adjacent",
        name="Is Adjacent",
        description="Target is within 5 feet (melee range)",
        category=RuleCategory.COMBAT,
        scope=RuleScope.INTERACTION,
        spec_class=IsAdjacent,
        parameters=[],
        icon="🤝",
        tags=["melee", "adjacent", "range"],
        is_base_rule=False,
        examples=["Required for melee attacks and opportunity attacks"],
    ))
    
    registry.register(RuleDefinition(
        rule_id="is_incapacitated",
        name="Is Incapacitated",
        description="Entity cannot take actions (stunned, paralyzed, unconscious, etc.)",
        category=RuleCategory.CONDITIONS,
        scope=RuleScope.ENTITY,
        spec_class=IsIncapacitated,
        parameters=[],
        icon="💫",
        tags=["condition", "incapacitated", "disabled"],
        is_base_rule=False,
        is_invertible=True,
        examples=["Use ~IsIncapacitated to require entity CAN act"],
    ))
    
    registry.register(RuleDefinition(
        rule_id="can_take_reaction",
        name="Can Take Reaction",
        description="Entity has not used their reaction since their last turn",
        category=RuleCategory.COMBAT,
        scope=RuleScope.ENTITY,
        spec_class=CanTakeReaction,
        parameters=[],
        icon="⚡",
        tags=["reaction", "action economy"],
        is_base_rule=False,
        examples=["Required for opportunity attacks, Shield spell, etc."],
    ))


def _register_movement_rules(registry: RuleRegistry):
    """Register movement-related rules."""
    from domain.specs.movement import HasMovementRemaining, TileIsPassable, TileNotOccupied
    
    registry.register(RuleDefinition(
        rule_id="has_movement",
        name="Has Movement Remaining",
        description="Entity has enough movement speed left this turn",
        category=RuleCategory.MOVEMENT,
        scope=RuleScope.ENTITY,
        spec_class=HasMovementRemaining,
        parameters=[PARAM_DISTANCE],
        icon="🏃",
        tags=["movement", "speed", "resource"],
        is_base_rule=False,
        examples=["Check before allowing movement to a tile"],
    ))
    
    registry.register(RuleDefinition(
        rule_id="tile_passable",
        name="Tile Is Passable",
        description="Tile terrain allows movement (not a wall, lava, etc.)",
        category=RuleCategory.MOVEMENT,
        scope=RuleScope.TILE,
        spec_class=TileIsPassable,
        parameters=[
            RuleParameter(
                name="allow_difficult",
                param_type="bool",
                label="Allow Difficult Terrain",
                description="Whether difficult terrain counts as passable",
                default=True,
            ),
        ],
        icon="🚶",
        tags=["terrain", "passable", "blocking"],
        is_base_rule=False,
    ))
    
    registry.register(RuleDefinition(
        rule_id="tile_not_occupied",
        name="Tile Not Occupied",
        description="Tile is not blocked by another creature",
        category=RuleCategory.MOVEMENT,
        scope=RuleScope.TILE,
        spec_class=TileNotOccupied,
        parameters=[
            RuleParameter(
                name="allow_allies",
                param_type="bool",
                label="Allow Allies",
                description="Whether allied creatures block the tile",
                default=True,
            ),
        ],
        icon="🚫",
        tags=["occupation", "blocking", "creatures"],
        is_base_rule=False,
    ))


def _register_condition_rules(registry: RuleRegistry):
    """Register condition-checking rules."""
    from domain.specs.entity import HasCondition, HasHP, HasSpellSlot, IsEntityType
    
    registry.register(RuleDefinition(
        rule_id="has_condition",
        name="Has Condition",
        description="Entity has a specific condition",
        category=RuleCategory.CONDITIONS,
        scope=RuleScope.ENTITY,
        spec_class=HasCondition,
        parameters=[
            RuleParameter(
                name="condition",
                param_type="condition",
                label="Condition",
                description="The condition to check for",
                choices=[
                    "blinded", "charmed", "deafened", "frightened",
                    "grappled", "incapacitated", "invisible", "paralyzed",
                    "petrified", "poisoned", "prone", "restrained",
                    "stunned", "unconscious"
                ],
            ),
        ],
        icon="🏷️",
        tags=["condition", "status", "debuff"],
        is_base_rule=False,
        is_invertible=True,
        examples=[
            "HasCondition('prone') - entity is prone",
            "~HasCondition('invisible') - entity is NOT invisible",
        ],
    ))
    
    registry.register(RuleDefinition(
        rule_id="has_hp",
        name="Has HP",
        description="Entity has at least a specified amount of HP",
        category=RuleCategory.RESOURCES,
        scope=RuleScope.ENTITY,
        spec_class=HasHP,
        parameters=[
            RuleParameter(
                name="minimum",
                param_type="int",
                label="Minimum HP",
                description="Required HP amount",
                default=1,
                min_value=0,
            ),
        ],
        icon="💚",
        tags=["hp", "health", "resource"],
        is_base_rule=False,
    ))
    
    registry.register(RuleDefinition(
        rule_id="has_spell_slot",
        name="Has Spell Slot",
        description="Entity has a spell slot of the specified level",
        category=RuleCategory.SPELLCASTING,
        scope=RuleScope.ENTITY,
        spec_class=HasSpellSlot,
        parameters=[
            RuleParameter(
                name="level",
                param_type="int",
                label="Spell Level",
                description="Required spell slot level (1-9)",
                default=1,
                min_value=1,
                max_value=9,
            ),
        ],
        icon="✨",
        tags=["spell", "slot", "resource", "magic"],
        is_base_rule=False,
    ))
    
    registry.register(RuleDefinition(
        rule_id="is_entity_type",
        name="Is Entity Type",
        description="Entity is of a specific type (player, enemy, NPC, trap)",
        category=RuleCategory.BASE,
        scope=RuleScope.ENTITY,
        spec_class=IsEntityType,
        parameters=[
            RuleParameter(
                name="entity_type",
                param_type="entity_type",
                label="Entity Type",
                description="The type to check for",
                choices=["player", "enemy", "npc", "trap", "object"],
            ),
        ],
        icon="👤",
        tags=["type", "classification"],
        is_base_rule=False,
        examples=[
            "IsEntityType('player') - only affects players",
            "IsEntityType('enemy') - only affects enemies",
        ],
    ))


def _register_trigger_rules(registry: RuleRegistry):
    """Register trigger/trap template rules."""
    from domain.specs.triggers import perception_trap, enter_zone_trigger
    
    # These are templates/factories, not direct specs
    # They need special handling in the UI
    pass  # Handled separately in builder.py


# ─────────────────────────────────────────────────────────────────────────────
# Global Registry Instance
# ─────────────────────────────────────────────────────────────────────────────

_default_registry: RuleRegistry | None = None


def get_default_registry() -> RuleRegistry:
    """Get the global default rule registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = RuleRegistry()
        _default_registry.register_defaults()
    return _default_registry


def register_custom_rule(rule: RuleDefinition):
    """Register a custom rule in the default registry."""
    get_default_registry().register(rule)

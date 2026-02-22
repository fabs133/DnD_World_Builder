"""
D&D 5e Specification Pattern Implementation

This package provides a composable, testable rule system for D&D 5e.

Modules:
- base: Core Specification classes and composition operators
- checks: Skill checks, saving throws, contests
- movement: Movement, terrain, range specifications
- entity: Entity conditions, resources, combat state
- triggers: Trigger system using specifications
- migration: Adapters for legacy code
- registry: Rule catalog with metadata
- builder: Declarative rule construction
- ruleset: Active rule configuration for scenarios
- pack: Shareable rule collections
- repository: Community sharing via GitHub

Quick Start:
    from domain.specs import (
        SkillCheckSpec, HasCondition, InRange,
        TriggerSpec, EventType, ReactionResult,
    )
    
    # Create a perception trap
    trap = TriggerSpec(
        trigger_id="pit_trap",
        event_type=EventType.ENTER_TILE,
        pre_specs=[
            ~SkillCheckSpec("Perception", dc=15),  # Fires on failure
        ],
        reaction=lambda e, c: ReactionResult(
            success=True,
            description="You fall into a pit!",
            damage_dealt=10,
        ),
    )
"""

# Base classes
from domain.specs.base import (
    Specification,
    SpecResult,
    AndSpec,
    OrSpec,
    NotSpec,
    AllOf,
    AnyOf,
    AlwaysTrue,
    AlwaysFalse,
)

# Check specifications
from domain.specs.checks import (
    SkillCheckSpec,
    SavingThrowSpec,
    ContestSpec,
    AbilityCheckSpec,
)

# Movement specifications
from domain.specs.movement import (
    TerrainType,
    MovementMode,
    HasMovementRemaining,
    TileIsPassable,
    TileNotOccupied,
    InRange,
    IsAdjacent,
    CanReachTile,
    can_move_to,
)

# Entity specifications
from domain.specs.entity import (
    Condition,
    INCAPACITATING_CONDITIONS,
    ATTACK_DISADVANTAGE_CONDITIONS,
    HasCondition,
    IsIncapacitated,
    IsAlive,
    HasHP,
    HasSpellSlot,
    HasAbilityUse,
    IsEntityType,
    HasFaction,
    CanTakeAction,
    CanTakeBonusAction,
    CanTakeReaction,
)

# Trigger system
from domain.specs.triggers import (
    EventType,
    TriggerEvent,
    ReactionResult,
    TriggerEvaluation,
    TriggerSpec,
    TriggerEvaluator,
    perception_trap,
    enter_zone_trigger,
)

# Migration adapters
from domain.specs.migration import (
    LegacyConditionAdapter,
    LegacySkillCheckAdapter,
    adapt_legacy_condition,
    adapt_legacy_trigger,
    SpecRegistry,
    get_registry,
    spec_from_dict,
)

# Rule registry
from domain.specs.registry import (
    RuleCategory,
    RuleScope,
    RuleParameter,
    RuleDefinition,
    RuleRegistry,
    get_default_registry,
    register_custom_rule,
)

# Rule builder
from domain.specs.builder import (
    CompositionType,
    RuleComponent,
    RuleMask,
    RuleBuilder,
    MaskLibrary,
    get_default_library,
    trap_template,
    zone_effect_template,
    combat_prerequisite_template,
)

# Ruleset management
from domain.specs.ruleset import (
    RuleInstanceState,
    RuleInstance,
    CustomRule,
    Ruleset,
    RulesetManager,
    TriggerRuleBinding,
    create_default_ruleset,
    create_minimal_ruleset,
    create_dungeon_crawl_ruleset,
)

# Rule packs
from domain.specs.pack import (
    PackCategory,
    CompatibilityLevel,
    PackAuthor,
    PackDependency,
    PackStats,
    RulePack,
    ValidationResult,
    PackValidator,
    PackManager,
)

# Repository
from domain.specs.repository import (
    SortOrder,
    PackListing,
    RepositoryIndex,
    RepositoryClient,
    PublishResult,
    PackPublisher,
    IndexGenerator,
    Collection,
    FEATURED_COLLECTIONS,
)

__all__ = [
    # Base
    "Specification",
    "SpecResult",
    "AndSpec",
    "OrSpec",
    "NotSpec",
    "AllOf",
    "AnyOf",
    "AlwaysTrue",
    "AlwaysFalse",
    # Checks
    "SkillCheckSpec",
    "SavingThrowSpec",
    "ContestSpec",
    "AbilityCheckSpec",
    # Movement
    "TerrainType",
    "MovementMode",
    "HasMovementRemaining",
    "TileIsPassable",
    "TileNotOccupied",
    "InRange",
    "IsAdjacent",
    "CanReachTile",
    "can_move_to",
    # Entity
    "Condition",
    "INCAPACITATING_CONDITIONS",
    "ATTACK_DISADVANTAGE_CONDITIONS",
    "HasCondition",
    "IsIncapacitated",
    "IsAlive",
    "HasHP",
    "HasSpellSlot",
    "HasAbilityUse",
    "IsEntityType",
    "HasFaction",
    "CanTakeAction",
    "CanTakeBonusAction",
    "CanTakeReaction",
    # Triggers
    "EventType",
    "TriggerEvent",
    "ReactionResult",
    "TriggerEvaluation",
    "TriggerSpec",
    "TriggerEvaluator",
    "perception_trap",
    "enter_zone_trigger",
    # Migration
    "LegacyConditionAdapter",
    "LegacySkillCheckAdapter",
    "adapt_legacy_condition",
    "adapt_legacy_trigger",
    "SpecRegistry",
    "get_registry",
    "spec_from_dict",
    # Registry
    "RuleCategory",
    "RuleScope",
    "RuleParameter",
    "RuleDefinition",
    "RuleRegistry",
    "get_default_registry",
    "register_custom_rule",
    # Builder
    "CompositionType",
    "RuleComponent",
    "RuleMask",
    "RuleBuilder",
    "MaskLibrary",
    "get_default_library",
    "trap_template",
    "zone_effect_template",
    "combat_prerequisite_template",
    # Ruleset
    "RuleInstanceState",
    "RuleInstance",
    "CustomRule",
    "Ruleset",
    "RulesetManager",
    "TriggerRuleBinding",
    "create_default_ruleset",
    "create_minimal_ruleset",
    "create_dungeon_crawl_ruleset",
    # Packs
    "PackCategory",
    "CompatibilityLevel",
    "PackAuthor",
    "PackDependency",
    "PackStats",
    "RulePack",
    "ValidationResult",
    "PackValidator",
    "PackManager",
    # Repository
    "SortOrder",
    "PackListing",
    "RepositoryIndex",
    "RepositoryClient",
    "PublishResult",
    "PackPublisher",
    "IndexGenerator",
    "Collection",
    "FEATURED_COLLECTIONS",
]

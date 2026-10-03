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
    AllOf,
    AlwaysFalse,
    AlwaysTrue,
    AndSpec,
    AnyOf,
    NotSpec,
    OrSpec,
    Specification,
    SpecResult,
)

# Rule builder
from domain.specs.builder import (
    CompositionType,
    MaskLibrary,
    RuleBuilder,
    RuleComponent,
    RuleMask,
    combat_prerequisite_template,
    get_default_library,
    trap_template,
    zone_effect_template,
)

# Check specifications
from domain.specs.checks import (
    ContestSpec,
    SavingThrowSpec,
    SkillCheckSpec,
)

# Entity specifications
from domain.specs.entity import (
    ATTACK_DISADVANTAGE_CONDITIONS,
    INCAPACITATING_CONDITIONS,
    CanTakeAction,
    CanTakeBonusAction,
    CanTakeReaction,
    Condition,
    HasAbilityUse,
    HasCondition,
    HasFaction,
    HasHP,
    HasSpellSlot,
    IsAlive,
    IsEntityType,
    IsIncapacitated,
)

# Migration adapters
from domain.specs.migration import (
    LegacyConditionAdapter,
    LegacySkillCheckAdapter,
    SpecRegistry,
    adapt_legacy_condition,
    adapt_legacy_trigger,
    get_registry,
    spec_from_dict,
)

# Movement specifications
from domain.specs.movement import (
    CanReachTile,
    HasMovementRemaining,
    InRange,
    IsAdjacent,
    MovementMode,
    TerrainType,
    TileIsPassable,
    TileNotOccupied,
    can_move_to,
)

# Rule packs
from domain.specs.pack import (
    CompatibilityLevel,
    PackAuthor,
    PackCategory,
    PackDependency,
    PackManager,
    PackStats,
    PackValidator,
    RulePack,
    ValidationResult,
)

# Rule registry
from domain.specs.registry import (
    RuleCategory,
    RuleDefinition,
    RuleParameter,
    RuleRegistry,
    RuleScope,
    get_default_registry,
    register_custom_rule,
)

# Repository
from domain.specs.repository import (
    FEATURED_COLLECTIONS,
    Collection,
    IndexGenerator,
    PackListing,
    PackPublisher,
    PublishResult,
    RepositoryClient,
    RepositoryIndex,
    SortOrder,
)

# Ruleset management
from domain.specs.ruleset import (
    CustomRule,
    RuleInstance,
    RuleInstanceState,
    Ruleset,
    RulesetManager,
    TriggerRuleBinding,
    create_default_ruleset,
    create_dungeon_crawl_ruleset,
    create_minimal_ruleset,
)

# Trigger system
from domain.specs.triggers import (
    EventType,
    ReactionResult,
    TriggerEvaluation,
    TriggerEvaluator,
    TriggerEvent,
    TriggerSpec,
    enter_zone_trigger,
    perception_trap,
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
